"""The Analyze buttons: one job from its card, or the newest few in the New column.

Same shape as a discovery run — the dashboard's token is used for this run only,
the work happens in the background, and the dashboard polls for progress. One run
at a time: each job costs a few LLM calls, and two runs would compete for the same
hosted rate limit while making the cost of a click hard to predict.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Literal

import httpx
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, model_validator

from agents import analysis
from agents.analysis import AnalysisOutcome
from api.discovery import Caller
from mcp_servers.jobpilot_api import client
from mcp_servers.jobpilot_api.client import JobPilotApiError

router = APIRouter(tags=["analysis"])

# A bulk click analyzes at most this many — about $0.05 and several minutes. More is
# another click, so the cost of each one stays small and visible.
MAX_PER_RUN = 50

EXPIRED = "Your session expired mid-run. Run again — finished jobs keep their results."


class AnalysisRequest(BaseModel):
    """Exactly one of the two: specific jobs, or the newest `newest` in New."""

    jobIds: list[str] | None = Field(default=None, min_length=1, max_length=MAX_PER_RUN)
    newest: int | None = Field(default=None, ge=1, le=MAX_PER_RUN)

    @model_validator(mode="after")
    def one_of(self) -> AnalysisRequest:
        if (self.jobIds is None) == (self.newest is None):
            raise ValueError("send either jobIds or newest")
        return self


class AnalysisRun(BaseModel):
    id: str
    status: Literal["running", "done", "failed"]
    # Every job in the run, so the board can mark which cards are waiting.
    jobIds: list[str]
    results: list[AnalysisOutcome] = Field(default_factory=list)
    error: str | None = None
    startedAt: datetime
    finishedAt: datetime | None = None


class _Slot:
    """The one run, in memory. Each job's results are written to the server as it
    finishes, so a restart here loses only the progress view."""

    run: AnalysisRun | None = None
    owner: str | None = None
    task: asyncio.Task[None] | None = None


_slot = _Slot()


@router.post("/run", response_model=AnalysisRun, status_code=status.HTTP_202_ACCEPTED)
async def start_run(body: AnalysisRequest, who: Caller) -> AnalysisRun:
    token, account_id = who
    if _slot.run is not None and _slot.run.status == "running":
        raise HTTPException(status.HTTP_409_CONFLICT, "an analysis run is already in progress")

    if body.jobIds is not None:
        job_ids = list(dict.fromkeys(body.jobIds))
    else:
        try:
            newest = await client.list_jobs(status="new", limit=body.newest or 1)
        except (JobPilotApiError, httpx.HTTPError) as error:
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY, f"could not list jobs: {error}"
            ) from error
        job_ids = [job["id"] for job in newest]
        if not job_ids:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "no new jobs to analyze")

    run = AnalysisRun(
        id=uuid.uuid4().hex, status="running", jobIds=job_ids, startedAt=datetime.now(UTC)
    )
    _slot.run, _slot.owner = run, account_id
    _slot.task = asyncio.create_task(_execute(run, token))
    return run


@router.get("/run", response_model=AnalysisRun | None)
async def latest_run(who: Caller) -> AnalysisRun | None:
    """The latest run, if the caller started it. Another account sees nothing."""
    _, account_id = who
    return _slot.run if _slot.owner == account_id else None


async def _execute(run: AnalysisRun, token: str) -> None:
    client.set_token(token)
    try:
        await analysis.analyze_many(run.jobIds, on_result=run.results.append)
        run.status = "done"
    except JobPilotApiError as error:
        run.status = "failed"
        run.error = EXPIRED if error.status == 401 else str(error)[:300]
    except Exception as error:  # noqa: BLE001 — a background task has no caller to raise to
        run.status = "failed"
        run.error = f"{type(error).__name__}: {error}"[:300]
    finally:
        run.finishedAt = datetime.now(UTC)
