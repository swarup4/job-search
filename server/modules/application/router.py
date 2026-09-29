from typing import Literal

from beanie import PydanticObjectId
from fastapi import APIRouter, Query

from modules.account import CurrentUser
from modules.application import service
from modules.application.models import (
    AnswerBank,
    ApplicantFields,
    ApplicantProfile,
    ApplicantRead,
    Application,
    ApplicationFill,
    ApplicationRead,
    ApplicationStatus,
    Board,
    BoardCard,
    ShortlistRow,
    StatusTransition,
    Tracker,
)

router = APIRouter(tags=["application"])


# --- the applicant's standing answers ----------------------------------------


@router.get("/applicant", response_model=ApplicantRead)
async def get_applicant(user_id: CurrentUser) -> ApplicantProfile:
    return await service.get_applicant(user_id)


@router.put("/applicant", response_model=ApplicantRead)
async def save_applicant(payload: ApplicantFields, user_id: CurrentUser) -> ApplicantProfile:
    return await service.save_applicant(user_id, payload)


@router.get("/answer-bank", response_model=list[AnswerBank])
async def answer_bank(user_id: CurrentUser) -> list[AnswerBank]:
    """Read by the extension's background worker for screening questions."""
    return await service.list_answer_bank(user_id)


@router.get("/tracker", response_model=Tracker)
async def tracker(user_id: CurrentUser) -> Tracker:
    """The Applications screen in one call: staged and submitted, with each job joined."""
    return await service.tracker(user_id)


BoardColumnKey = Literal["new", "shortlisted", "staged", "applied", "interview"]


@router.get("/board", response_model=Board)
async def board(user_id: CurrentUser, limit: int = Query(default=5, ge=1, le=50)) -> Board:
    return await service.board(user_id, limit)


@router.get("/board/{column}", response_model=list[BoardCard])
async def board_column(
    column: BoardColumnKey,
    user_id: CurrentUser,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=5, ge=1, le=50),
) -> list[BoardCard]:
    return await service.board_column(user_id, column, skip, limit)


@router.get("/shortlist", response_model=list[ShortlistRow])
async def shortlisted_jobs(user_id: CurrentUser) -> list[ShortlistRow]:
    return await service.shortlisted_jobs(user_id)


@router.post("/shortlist/{job_id}", response_model=ApplicationRead)
async def shortlist(job_id: PydanticObjectId, user_id: CurrentUser) -> Application:
    return await service.shortlist(user_id, job_id)


@router.delete("/shortlist/{job_id}", response_model=ApplicationRead | None)
async def unshortlist(job_id: PydanticObjectId, user_id: CurrentUser) -> Application | None:
    return await service.unshortlist(user_id, job_id)


@router.post("/fill/{application_id}", response_model=ApplicationRead)
async def record_fill(
    application_id: PydanticObjectId, payload: ApplicationFill, user_id: CurrentUser
) -> Application:
    return await service.record_fill(user_id, application_id, payload)


@router.patch("/status/{application_id}", response_model=ApplicationRead)
async def set_status(
    application_id: PydanticObjectId, payload: StatusTransition, user_id: CurrentUser
) -> Application:
    return await service.set_status(user_id, application_id, payload)


@router.get("", response_model=list[ApplicationRead])
async def list_applications(
    user_id: CurrentUser,
    statuses: list[ApplicationStatus] | None = Query(default=None, alias="status"),
) -> list[Application]:
    return await service.list_applications(user_id, statuses)
