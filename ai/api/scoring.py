"""Score every job you have no match for — the header's Refresh, or by hand:

    curl -X POST http://127.0.0.1:8001/api/runs/scoring/start -H "Authorization: Bearer <token>"

A background run on the match model (`MATCH_LLM_*` in `.env`, a local one if set),
one job at a time, until nothing unscored is left — so jobs discovered mid-run are
picked up too. Jobs you already have a match for are never touched, so keyword
selections survive. Progress streams from `GET /api/runs/scoring/events`, from `run_started`, which
carries the run.

Starting while your run is going returns that run rather than a second one: Refresh
clicked twice means "show me the progress". Another account gets a 409.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Header, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from agents import matching
from api.discovery import Caller
from api.events import EventLog
from mcp_servers.jobpilot_api import client
from mcp_servers.jobpilot_api.client import JobPilotApiError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["scoring"])

# The server's page size for unscored jobs; the run keeps asking until none are left.
BATCH = 50

EXPIRED = "Your session expired mid-run. Refresh again — jobs already scored keep their match."


class ScoringResult(BaseModel):
    jobId: str
    title: str = ""
    score: int | None = None
    error: str | None = None


class ScoringRun(BaseModel):
    id: str
    status: Literal["running", "done", "failed"]
    scored: int = 0
    failed: int = 0
    results: list[ScoringResult] = Field(default_factory=list)
    error: str | None = None
    startedAt: datetime
    finishedAt: datetime | None = None


class _Slot:
    """The one run, in memory. Each match is written to the server as it is made, so a
    restart here loses only the progress view."""

    def __init__(self) -> None:
        self.run: ScoringRun | None = None
        self.owner: str | None = None
        self.task: asyncio.Task[None] | None = None
        self.log = EventLog()


_slot = _Slot()


@router.post("/start", response_model=ScoringRun, status_code=status.HTTP_202_ACCEPTED)
async def start_scoring(who: Caller, response: Response) -> ScoringRun:
    token, account_id = who
    if _slot.run is not None and _slot.run.status == "running":
        if _slot.owner != account_id:
            raise HTTPException(status.HTTP_409_CONFLICT, "a scoring run is already in progress")
        response.status_code = status.HTTP_200_OK
        return _slot.run

    run = ScoringRun(id=uuid.uuid4().hex, status="running", startedAt=datetime.now(UTC))
    _slot.run, _slot.owner, _slot.log = run, account_id, EventLog()
    _slot.task = asyncio.create_task(_execute(run, token, _slot.log))
    return run


@router.get("/events")
async def scoring_events(
    request: Request,
    who: Caller,
    last_event_id: Annotated[str | None, Header()] = None,
) -> Response:
    _, account_id = who
    if _slot.run is None or _slot.owner != account_id:
        # "You have no run yet" is an answer, not an error: nothing to stream.
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    run = _slot.run
    return _slot.log.stream(request, last_event_id, lambda: _slot.run is run)


async def _execute(run: ScoringRun, token: str, log: EventLog) -> None:
    client.set_token(token)
    log.emit({"type": "run_started", "run": run.model_dump(mode="json")})
    # A job that failed stays unscored and would come back in every batch.
    attempted: set[str] = set()
    try:
        while True:
            batch = [
                job
                for job in await client.list_unscored_jobs(limit=BATCH)
                if job["id"] not in attempted
            ]
            if not batch:
                break
            for job in batch:
                attempted.add(job["id"])
                result = await _score_one(job, log)
                if result.error is None:
                    run.scored += 1
                else:
                    run.failed += 1
                run.results.append(result)
                log.emit(
                    {"type": "job_done", **result.model_dump(), "scored": run.scored,
                     "failed": run.failed}
                )  # fmt: skip
        run.status = "done"
    except JobPilotApiError as error:
        run.status = "failed"
        run.error = EXPIRED if error.status == 401 else str(error)[:300]
        if error.status != 401:
            logger.error("scoring run %s failed: %s", run.id, error)
    except Exception as error:  # a background task has no caller to raise to
        logger.exception("scoring run %s failed", run.id)
        run.status = "failed"
        run.error = f"{type(error).__name__}: {error}"[:300]
    finally:
        run.finishedAt = datetime.now(UTC)
        log.emit(
            {"type": "run_done", "status": run.status, "error": run.error, "scored": run.scored,
             "failed": run.failed, "finishedAt": run.finishedAt.isoformat()}
        )  # fmt: skip


async def _score_one(job: dict[str, str], log: EventLog) -> ScoringResult:
    """One job; its failure is recorded, not raised — except a dead token, which would
    fail every later job the same way and so ends the run."""
    title = job.get("title", "")
    log.emit({"type": "job_started", "jobId": job["id"], "title": title})
    try:
        match = await matching.score_job(job["id"])
    except JobPilotApiError as error:
        if error.status == 401:
            raise
        logger.error("scoring job %s failed: %s", job["id"], error)
        return ScoringResult(jobId=job["id"], title=title, error=str(error)[:200])
    except Exception as error:  # one job's failure must not stop the rest
        logger.exception("scoring job %s failed", job["id"])
        return ScoringResult(
            jobId=job["id"], title=title, error=f"{type(error).__name__}: {error}"[:200]
        )
    return ScoringResult(jobId=job["id"], title=title, score=match.get("score"))
