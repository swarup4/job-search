from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Header, Request, Response, status

from api.deps import Caller
from api.scoring import service
from api.scoring.models import ScoringRun

router = APIRouter(tags=["scoring"])


@router.post("/start", response_model=ScoringRun, status_code=status.HTTP_202_ACCEPTED)
async def start_scoring(who: Caller, response: Response) -> ScoringRun:
    token, account_id = who
    run, started = service.start(token, account_id)
    if not started:
        response.status_code = status.HTTP_200_OK
    return run


@router.get("/events")
async def scoring_events(
    request: Request,
    who: Caller,
    last_event_id: Annotated[str | None, Header()] = None,
) -> Response:
    _, account_id = who
    return service.events(request, account_id, last_event_id)
