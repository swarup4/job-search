"""The Analyze buttons: one job from its page, or the newest few you have not scored yet.

Same shape as a discovery run — the dashboard's token is used for this run only and
the work happens in the background. `start` begins one (or hands back yours, if going);
progress is pushed as server-sent events from `events`, one per step as it starts and
ends, from `run_started`, which carries the run. One run at a time: each job costs a
few LLM calls, and two runs would compete for the same hosted rate limit while making
the cost of a click hard to predict.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime

import httpx
from fastapi import Request, Response, status

from agents import analysis
from agents.analysis import AnalysisOutcome
from api.analysis.models import AnalysisRequest, AnalysisRun
from api.events import EventLog
from config.errors import BadGateway, Conflict, Invalid
from config.llm import track_usage
from mcp_servers.jobpilot_api import client
from mcp_servers.jobpilot_api.client import JobPilotApiError

logger = logging.getLogger(__name__)

EXPIRED = "Your session expired mid-run. Run again — finished jobs keep their results."


class _Slot:
    """The one run, in memory. Each job's results are written to the server as it
    finishes, so a restart here loses only the progress view."""

    def __init__(self) -> None:
        self.run: AnalysisRun | None = None
        self.owner: str | None = None
        self.task: asyncio.Task[None] | None = None
        self.log = EventLog()


_slot = _Slot()


async def start(token: str, account_id: str, request: AnalysisRequest) -> tuple[AnalysisRun, bool]:
    """The run, and whether this call started it — False when yours was already going."""
    if _slot.run is not None and _slot.run.status == "running":
        if _slot.owner != account_id:
            raise Conflict("an analysis run is already in progress")
        return _slot.run, False

    if request.jobIds is not None:
        job_ids = list(dict.fromkeys(request.jobIds))
    else:
        try:
            newest = await client.list_unscored_jobs(limit=request.newest or 1)
        except (JobPilotApiError, httpx.HTTPError) as error:
            raise BadGateway(f"could not list jobs: {error}") from error
        job_ids = [job["id"] for job in newest]
        if not job_ids:
            raise Invalid("no new jobs to analyze")

    run = AnalysisRun(
        id=uuid.uuid4().hex, status="running", jobIds=job_ids, startedAt=datetime.now(UTC)
    )
    _slot.run, _slot.owner, _slot.log = run, account_id, EventLog()
    _slot.task = asyncio.create_task(_execute(run, token))
    return run, True


def events(request: Request, account_id: str, last_event_id: str | None) -> Response:
    if _slot.run is None or _slot.owner != account_id:
        # "You have no run yet" is an answer, not an error: nothing to stream.
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    run = _slot.run
    return _slot.log.stream(request, last_event_id, lambda: _slot.run is run)


async def _execute(run: AnalysisRun, token: str) -> None:
    client.set_token(token)

    log = _slot.log
    log.emit({"type": "run_started", "run": run.model_dump(mode="json")})

    def finished(outcome: AnalysisOutcome) -> None:
        run.results.append(outcome)
        log.emit({"type": "job_done", **outcome.model_dump()})

    with track_usage() as usage:
        try:
            await analysis.analyze_many(run.jobIds, on_result=finished, on_event=log.emit)
            run.status = "done"
        except JobPilotApiError as error:
            run.status = "failed"
            run.error = EXPIRED if error.status == 401 else str(error)[:300]
            if error.status != 401:
                logger.error("analysis run %s failed: %s", run.id, error)
        except Exception as error:  # a background task has no caller to raise to
            logger.exception("analysis run %s failed", run.id)
            run.status = "failed"
            run.error = f"{type(error).__name__}: {error}"[:300]
        finally:
            run.finishedAt = datetime.now(UTC)
            logger.info(
                "analysis run %s: %d jobs, tokens %s", run.id, len(run.jobIds), usage.summary()
            )
            log.emit(
                {"type": "run_done", "status": run.status, "error": run.error,
                 "finishedAt": run.finishedAt.isoformat(), "usage": usage.summary()}
            )  # fmt: skip
