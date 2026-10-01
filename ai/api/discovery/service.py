"""The dashboard's way to start a scrape, as whoever is signed in.

`start` begins one (or hands back yours, if going) and `events` streams it — every
company as it finishes, from `run_started`, which carries the run. The JWT arrives on
the request and is handed to the client with `set_token` for that run only; nothing
keeps it past the run. One run at a time, because two overlapping runs would race
each other's duplicate checks and write the same postings twice.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import Request, Response, status

from api.discovery.models import CompanyResult, DiscoveryRun
from api.events import EventLog
from config.errors import Conflict, Invalid
from mcp_servers.jobpilot_api import client
from mcp_servers.jobpilot_api.client import JobPilotApiError
from sources import run as scrape
from sources.base import Filters

logger = logging.getLogger(__name__)

EXPIRED = "Your session expired mid-run. Run again — jobs already stored are skipped."


class _Slot:
    """The one run. In memory: each company's outcome is written to its career source
    as it finishes, so a restart loses only the progress view, never the result."""

    def __init__(self) -> None:
        self.run: DiscoveryRun | None = None
        self.owner: str | None = None
        # Held so the event loop's weak reference is not the only one to the task.
        self.task: asyncio.Task[None] | None = None
        self.log = EventLog()


_slot = _Slot()


async def start(token: str, account_id: str, limit: int | None) -> tuple[DiscoveryRun, bool]:
    """The run, and whether this call started it — False when yours was already going."""
    if _slot.run is not None and _slot.run.status == "running":
        if _slot.owner != account_id:
            raise Conflict("a discovery run is already in progress")
        return _slot.run, False

    sources = await client.list_career_sources(enabled=True)
    filters = Filters.from_preferences(await client.get_preferences())
    if not sources:
        raise Invalid("no enabled career sources — seed them with server/seed_career_sources.py")

    run = DiscoveryRun(
        id=uuid.uuid4().hex,
        status="running",
        companies=len(sources),
        limit=limit,
        filters=filters,
        startedAt=datetime.now(UTC),
    )
    _slot.run, _slot.owner, _slot.log = run, account_id, EventLog()
    _slot.task = asyncio.create_task(_execute(run, token, sources, _slot.log))
    return run, True


def events(request: Request, account_id: str, last_event_id: str | None) -> Response:
    if _slot.run is None or _slot.owner != account_id:
        # "You have no run yet" is an answer, not an error: nothing to stream.
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    run = _slot.run
    return _slot.log.stream(request, last_event_id, lambda: _slot.run is run)


async def _execute(
    run: DiscoveryRun, token: str, sources: list[dict[str, Any]], log: EventLog
) -> None:
    client.set_token(token)
    log.emit({"type": "run_started", "run": run.model_dump(mode="json")})

    def record(name: str, result: dict[str, Any]) -> None:
        company = CompanyResult(name=name, **result)
        run.results.append(company)
        log.emit({"type": "company_done", **company.model_dump(), "done": len(run.results)})

    try:
        await scrape.run_all(sources, run.filters, on_result=record, limit=run.limit)
        run.status = "done"
    except JobPilotApiError as error:
        run.status = "failed"
        run.error = EXPIRED if error.status == 401 else str(error)[:300]
        if error.status != 401:
            logger.error("discovery run %s failed: %s", run.id, error)
    except Exception as error:  # a background task has no caller to raise to
        logger.exception("discovery run %s failed", run.id)
        run.status = "failed"
        run.error = f"{type(error).__name__}: {error}"[:300]
    finally:
        run.finishedAt = datetime.now(UTC)
        log.emit(
            {"type": "run_done", "status": run.status, "error": run.error,
             "finishedAt": run.finishedAt.isoformat(), "limit": run.limit,
             "new": sum(result.new for result in run.results)}
        )  # fmt: skip
