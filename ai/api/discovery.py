"""The dashboard's way to start a scrape, as whoever is signed in.

The JWT arrives on the request and is handed to the client with `set_token` for
that run only; nothing keeps it past the run. One run at a time, because two
overlapping runs would race each other's duplicate checks and write the same
postings twice.
"""

from __future__ import annotations

import asyncio
import hashlib
import time
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any, Literal

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

from mcp_servers.jobpilot_api import client
from mcp_servers.jobpilot_api.client import JobPilotApiError
from sources import run as scrape
from sources.base import Filters

router = APIRouter(tags=["discovery"])

EXPIRED = "Your session expired mid-run. Run again — jobs already stored are skipped."

# The dashboard polls while a run is going. Without this, every poll would cost the
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
    error: str | None = None


class DiscoveryRun(BaseModel):
    id: str
    status: Literal["running", "done", "failed"]
    companies: int
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

    run: DiscoveryRun | None = None
    owner: str | None = None
    # Held so the event loop's weak reference is not the only one to the task.
    task: asyncio.Task[None] | None = None


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


@router.post("/run", response_model=DiscoveryRun, status_code=status.HTTP_202_ACCEPTED)
async def start_run(who: Caller) -> DiscoveryRun:
    token, account_id = who
    if _slot.run is not None and _slot.run.status == "running":
        raise HTTPException(status.HTTP_409_CONFLICT, "a discovery run is already in progress")

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
        filters=filters,
        startedAt=datetime.now(UTC),
    )
    _slot.run, _slot.owner = run, account_id
    _slot.task = asyncio.create_task(_execute(run, token, sources))
    return run


@router.get("/run", response_model=DiscoveryRun | None)
async def latest_run(who: Caller) -> DiscoveryRun | None:
    """The latest run, if the caller started it. Another account sees nothing."""
    _, account_id = who
    return _slot.run if _slot.owner == account_id else None


async def _execute(run: DiscoveryRun, token: str, sources: list[dict[str, Any]]) -> None:
    client.set_token(token)

    def record(name: str, result: dict[str, Any]) -> None:
        run.results.append(CompanyResult(name=name, **result))

    try:
        await scrape.run_all(sources, run.filters, on_result=record)
        run.status = "done"
    except JobPilotApiError as error:
        run.status = "failed"
        run.error = EXPIRED if error.status == 401 else str(error)[:300]
    except Exception as error:  # noqa: BLE001 — a background task has no caller to raise to
        run.status = "failed"
        run.error = f"{type(error).__name__}: {error}"[:300]
    finally:
        run.finishedAt = datetime.now(UTC)
