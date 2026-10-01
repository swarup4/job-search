from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Header, Request, Response, status

from api.deps import Caller
from api.discovery import service
from api.discovery.models import DiscoveryRequest, DiscoveryRun

router = APIRouter(tags=["discovery"])


@router.post("/start", response_model=DiscoveryRun, status_code=status.HTTP_202_ACCEPTED)
async def start_discovery(
    who: Caller, response: Response, body: DiscoveryRequest | None = None
) -> DiscoveryRun:
    token, account_id = who
    run, started = await service.start(token, account_id, body.limit if body else None)
    if not started:
        # Yours already: answer it, and the page follows it rather than showing an error.
        response.status_code = status.HTTP_200_OK
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
    return service.events(request, account_id, last_event_id)
