"""The dashboard's way to start a scrape, as whoever is signed in.

`POST /api/runs/discovery/start` starts one (or answers yours, if going) and `/events`
streams it — every company as it finishes, from `run_started`, which carries the run. The JWT arrives on the request and is handed to the
client with `set_token` for that run only; nothing keeps it past the run. One run at a time, because two
overlapping runs would race each other's duplicate checks and write the same
postings twice.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any, Literal

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from api.events import EventLog
from mcp_servers.jobpilot_api import client
from mcp_servers.jobpilot_api.client import JobPilotApiError
from sources import run as scrape
from sources.base import Filters

logger = logging.getLogger(__name__)

router = APIRouter(tags=["discovery"])

EXPIRED = "Your session expired mid-run. Run again — jobs already stored are skipped."

# Every request on this tier checks its token. Without this, each one would cost the
# API server a getAccount as well. The price: a token that has just expired is still
# accepted here for up to this long. Harmless — it can only read progress or start a
# run, and a run's first call to the API server is refused.
VERIFIED_FOR = 60.0


class CompanyResult(BaseModel):
    name: str
    fetched: int = 0
    matched: int = 0
    new: int = 0
    duplicate: int = 0
    failed: int = 0
    blocked: bool = False
    # Not scraped: the run's limit was reached before this company's turn.
    skipped: bool = False
    # Of `matched`, how many came in on a skill in the description, not a role in the title.
    bySkill: int = 0
    error: str | None = None


class DiscoveryRequest(BaseModel):
    """`limit` stops the run once that many new jobs are stored. Omitted, every enabled
    company is scraped in full, filtered by your Search targets."""

    limit: int | None = Field(default=None, ge=1, le=500)


class DiscoveryRun(BaseModel):
    id: str
    status: Literal["running", "done", "failed"]
    companies: int
    # How many new jobs this run was asked for; null means every one it finds.
    limit: int | None = None
    # The Search targets this run was started with, read once at the start — so a
    # change saved mid-run applies to the next run, and the screen can show which.
    filters: Filters
    results: list[CompanyResult] = Field(default_factory=list)
    error: str | None = None
    startedAt: datetime
    finishedAt: datetime | None = None


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

# sha256 of a token -> (account id, when the server last confirmed it). Hashed so no
# token sits in memory longer than the request that carried it.
_verified: dict[str, tuple[str, float]] = {}


async def caller(authorization: Annotated[str | None, Header()] = None) -> tuple[str, str]:
    """The forwarded token and whose it is. This tier has no secret to verify a JWT
    with, so it asks the server — which also proves the token still works."""
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing bearer token")

    client.set_token(token)
    key = hashlib.sha256(token.encode()).hexdigest()
    now = time.monotonic()
    cached = _verified.get(key)
    if cached is not None and now - cached[1] < VERIFIED_FOR:
        return token, cached[0]

    try:
        account = await client.get_account()
    except JobPilotApiError as error:
        code = error.status if error.status == 401 else status.HTTP_502_BAD_GATEWAY
        raise HTTPException(code, error.detail) from error
    except httpx.HTTPError as error:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "cannot reach the JobPilot API") from error

    # Tokens rotate hourly, so old entries are dropped rather than left to pile up.
    for stale in [k for k, (_, at) in _verified.items() if now - at >= VERIFIED_FOR]:
        del _verified[stale]
    _verified[key] = (account["id"], now)
    return token, account["id"]


Caller = Annotated[tuple[str, str], Depends(caller)]


@router.post("/start", response_model=DiscoveryRun, status_code=status.HTTP_202_ACCEPTED)
async def start_discovery(
    who: Caller, response: Response, body: DiscoveryRequest | None = None
) -> DiscoveryRun:
    token, account_id = who
    if _slot.run is not None and _slot.run.status == "running":
        if _slot.owner != account_id:
            raise HTTPException(status.HTTP_409_CONFLICT, "a discovery run is already in progress")
        # Yours already: answer it, and the page follows it rather than showing an error.
        response.status_code = status.HTTP_200_OK
        return _slot.run

    sources = await client.list_career_sources(enabled=True)
    filters = Filters.from_preferences(await client.get_preferences())
    if not sources:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "no enabled career sources — seed them with server/seed_career_sources.py",
        )

    run = DiscoveryRun(
        id=uuid.uuid4().hex,
        status="running",
        companies=len(sources),
        limit=body.limit if body else None,
        filters=filters,
        startedAt=datetime.now(UTC),
    )
    _slot.run, _slot.owner, _slot.log = run, account_id, EventLog()
    _slot.task = asyncio.create_task(_execute(run, token, sources, _slot.log))
    return run


@router.get("/events")
async def discovery_events(
    request: Request,
    who: Caller,
    last_event_id: Annotated[str | None, Header()] = None,
) -> Response:
    """Your latest run: `run_started` (the run itself), `company_done` as each company
    finishes, then `run_done`. 204 when you have none."""
    _, account_id = who
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
