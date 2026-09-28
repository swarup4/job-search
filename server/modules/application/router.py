from beanie import PydanticObjectId
from fastapi import APIRouter, Query, status

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
    ApplicationStage,
    ApplicationStatus,
    Badges,
    BoardCounts,
    StatusTransition,
    Tracker,
)
from modules.job import Job, JobRead

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


@router.get("/badges", response_model=Badges)
async def badges(user_id: CurrentUser) -> Badges:
    """The header and sidebar badges, and the Pipeline's review banner, in one call."""
    return await service.badges(user_id)


@router.get("/tracker", response_model=Tracker)
async def tracker(user_id: CurrentUser) -> Tracker:
    """The Applications screen in one call: staged and submitted, with each job joined."""
    return await service.tracker(user_id)


@router.get("/counts", response_model=BoardCounts)
async def board_counts(user_id: CurrentUser) -> BoardCounts:
    return await service.board_counts(user_id)


@router.get("/unstarted", response_model=list[JobRead])
async def unstarted_jobs(
    user_id: CurrentUser, limit: int = Query(default=50, le=200), skip: int = 0
) -> list[Job]:
    return await service.unstarted_jobs(user_id, limit, skip)


@router.post("/shortlist/{job_id}", response_model=ApplicationRead)
async def shortlist(job_id: PydanticObjectId, user_id: CurrentUser) -> Application:
    return await service.shortlist(user_id, job_id)


@router.delete("/shortlist/{job_id}", response_model=ApplicationRead | None)
async def unshortlist(job_id: PydanticObjectId, user_id: CurrentUser) -> Application | None:
    return await service.unshortlist(user_id, job_id)


@router.get("/for-job/{job_id}", response_model=ApplicationRead | None)
async def get_for_job(job_id: PydanticObjectId, user_id: CurrentUser) -> Application | None:
    return await service.get_for_job(user_id, job_id)


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


@router.post(
    "/stageApplication", response_model=ApplicationRead, status_code=status.HTTP_201_CREATED
)
async def stage_application(payload: ApplicationStage, user_id: CurrentUser) -> Application:
    return await service.stage_application(user_id, payload)


@router.get("/getApplication/{application_id}", response_model=ApplicationRead)
async def get_application(application_id: PydanticObjectId, user_id: CurrentUser) -> Application:
    return await service.get_application(user_id, application_id)
