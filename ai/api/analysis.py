"""The Analyze buttons: one job from its page, or the newest few you have not scored yet.

Same shape as a discovery run — the dashboard's token is used for this run only and
the work happens in the background. `POST /api/runs/analysis/start` starts one (or answers yours, if going);
progress is pushed as server-sent events from `GET /api/runs/analysis/events`, one per
step as it starts and ends, from `run_started`, which carries the run. One run at a time: each job costs a few LLM calls, and two runs would compete for the same
hosted rate limit while making the cost of a click hard to predict.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Annotated, Literal

import httpx
from fastapi import APIRouter, Header, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, model_validator

from agents import analysis
from agents.analysis import AnalysisOutcome
from api.discovery import Caller
from api.events import EventLog
from mcp_servers.jobpilot_api import client
from mcp_servers.jobpilot_api.client import JobPilotApiError

router = APIRouter(tags=["analysis"])

# A bulk click analyzes at most this many — about $0.05 and several minutes. More is
# another click, so the cost of each one stays small and visible.
MAX_PER_RUN = 50

EXPIRED = "Your session expired mid-run. Run again — finished jobs keep their results."


class AnalysisRequest(BaseModel):
    """Exactly one of the two: specific jobs, or the newest `newest` unscored ones."""

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

    def __init__(self) -> None:
        self.run: AnalysisRun | None = None
        self.owner: str | None = None
        self.task: asyncio.Task[None] | None = None
        self.log = EventLog()


_slot = _Slot()


@router.post("/start", response_model=AnalysisRun, status_code=status.HTTP_202_ACCEPTED)
async def start_analysis(body: AnalysisRequest, who: Caller, response: Response) -> AnalysisRun:
    token, account_id = who
    if _slot.run is not None and _slot.run.status == "running":
        if _slot.owner != account_id:
            raise HTTPException(status.HTTP_409_CONFLICT, "an analysis run is already in progress")
        # Yours already: answer it, and the page follows it rather than showing an error.
        response.status_code = status.HTTP_200_OK
        return _slot.run

    if body.jobIds is not None:
        job_ids = list(dict.fromkeys(body.jobIds))
    else:
        try:
            newest = await client.list_unscored_jobs(limit=body.newest or 1)
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
    _slot.run, _slot.owner, _slot.log = run, account_id, EventLog()
    _slot.task = asyncio.create_task(_execute(run, token))
    return run


@router.get("/events")
async def analysis_events(
    request: Request,
    who: Caller,
    last_event_id: Annotated[str | None, Header()] = None,
) -> StreamingResponse:
    """The caller's latest run as a stream: every event so far, then each new one,
    closing after `run_done`. `Last-Event-ID` resumes after a dropped connection."""
    _, account_id = who
    if _slot.run is None or _slot.owner != account_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no analysis run to follow")
    run = _slot.run
    return _slot.log.stream(request, last_event_id, lambda: _slot.run is run)


async def _execute(run: AnalysisRun, token: str) -> None:
    client.set_token(token)

    log = _slot.log
    log.emit({"type": "run_started", "run": run.model_dump(mode="json")})

    def finished(outcome: AnalysisOutcome) -> None:
        run.results.append(outcome)
        log.emit({"type": "job_done", **outcome.model_dump()})

    try:
        await analysis.analyze_many(run.jobIds, on_result=finished, on_event=log.emit)
        run.status = "done"
    except JobPilotApiError as error:
        run.status = "failed"
        run.error = EXPIRED if error.status == 401 else str(error)[:300]
    except Exception as error:  # noqa: BLE001 — a background task has no caller to raise to
        run.status = "failed"
        run.error = f"{type(error).__name__}: {error}"[:300]
    finally:
        run.finishedAt = datetime.now(UTC)
        log.emit(
            {"type": "run_done", "status": run.status, "error": run.error,
             "finishedAt": run.finishedAt.isoformat()}
        )  # fmt: skip
