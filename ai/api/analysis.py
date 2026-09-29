"""The Analyze buttons: one job from its page, or the newest few you have not scored yet.

Same shape as a discovery run — the dashboard's token is used for this run only and
the work happens in the background. Progress is pushed as server-sent events from
`GET /run/events`, one per step as it starts and ends; `GET /run` still answers the
run's state for a page that only needs the summary. One run at a time: each job costs a few LLM calls, and two runs would compete for the same
hosted rate limit while making the cost of a click hard to predict.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Annotated, Any, Literal

import httpx
from fastapi import APIRouter, Header, HTTPException, Request, status
from fastapi.responses import StreamingResponse
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

# A comment line this often keeps an idle stream from being closed as dead while a
# slow model call is in flight.
KEEPALIVE_SECONDS = 15


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
        # Every event of the run, kept so a stream opened late replays what it missed.
        self.events: list[dict[str, Any]] = []
        # Replaced on every event: each waiting stream holds the old one, which is set.
        self.tick = asyncio.Event()


def _emit(event: dict[str, Any]) -> None:
    _slot.events.append(event)
    tick, _slot.tick = _slot.tick, asyncio.Event()
    tick.set()


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
    _slot.run, _slot.owner, _slot.events = run, account_id, []
    _slot.task = asyncio.create_task(_execute(run, token))
    return run


@router.get("/run", response_model=AnalysisRun | None)
async def latest_run(who: Caller) -> AnalysisRun | None:
    """The latest run, if the caller started it. Another account sees nothing."""
    _, account_id = who
    return _slot.run if _slot.owner == account_id else None


@router.get("/run/events")
async def run_events(
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
    start = int(last_event_id) + 1 if last_event_id and last_event_id.isdigit() else 0

    async def stream() -> AsyncIterator[str]:
        index = start
        while True:
            tick = _slot.tick
            # A newer run replaced this one; its events are not this stream's.
            if _slot.run is not run:
                return
            while index < len(_slot.events):
                event = _slot.events[index]
                yield f"id: {index}\nevent: {event['type']}\ndata: {json.dumps(event)}\n\n"
                index += 1
                if event["type"] == "run_done":
                    return
            if await request.is_disconnected():
                return
            try:
                await asyncio.wait_for(tick.wait(), KEEPALIVE_SECONDS)
            except TimeoutError:
                yield ": keepalive\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _execute(run: AnalysisRun, token: str) -> None:
    client.set_token(token)

    def finished(outcome: AnalysisOutcome) -> None:
        run.results.append(outcome)
        _emit({"type": "job_done", **outcome.model_dump()})

    try:
        await analysis.analyze_many(run.jobIds, on_result=finished, on_event=_emit)
        run.status = "done"
    except JobPilotApiError as error:
        run.status = "failed"
        run.error = EXPIRED if error.status == 401 else str(error)[:300]
    except Exception as error:  # noqa: BLE001 — a background task has no caller to raise to
        run.status = "failed"
        run.error = f"{type(error).__name__}: {error}"[:300]
    finally:
        run.finishedAt = datetime.now(UTC)
        _emit({"type": "run_done", "status": run.status, "error": run.error})
