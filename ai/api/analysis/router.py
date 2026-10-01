from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Header, Request, Response, status

from api.analysis import service
from api.analysis.models import AnalysisRequest, AnalysisRun
from api.deps import Caller

router = APIRouter(tags=["analysis"])


@router.post("/start", response_model=AnalysisRun, status_code=status.HTTP_202_ACCEPTED)
async def start_analysis(body: AnalysisRequest, who: Caller, response: Response) -> AnalysisRun:
    token, account_id = who
    run, started = await service.start(token, account_id, body)
    if not started:
        # Yours already: answer it, and the page follows it rather than showing an error.
        response.status_code = status.HTTP_200_OK
    return run


@router.get("/events")
async def analysis_events(
    request: Request,
    who: Caller,
    last_event_id: Annotated[str | None, Header()] = None,
) -> Response:
    """The caller's latest run as a stream: every event so far, then each new one,
    closing after `run_done`. `Last-Event-ID` resumes after a dropped connection."""
    _, account_id = who
    return service.events(request, account_id, last_event_id)
