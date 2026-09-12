from beanie import PydanticObjectId
from fastapi import APIRouter, Query, status

from modules.account import CurrentUser
from modules.application import service
from modules.application.models import (
    AnswerBank,
    Application,
    ApplicationFill,
    ApplicationRead,
    ApplicationStage,
    ApplicationStatus,
    StatusTransition,
)

router = APIRouter(tags=["application"])


@router.get("/answer-bank", response_model=list[AnswerBank])
async def answer_bank(user_id: CurrentUser) -> list[AnswerBank]:
    """Read by the extension's background worker for screening questions."""
    return await service.list_answer_bank(user_id)


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
    application_status: ApplicationStatus | None = Query(default=None, alias="status"),
) -> list[Application]:
    return await service.list_applications(user_id, application_status)


@router.post("", response_model=ApplicationRead, status_code=status.HTTP_201_CREATED)
async def stage_application(payload: ApplicationStage, user_id: CurrentUser) -> Application:
    return await service.stage_application(user_id, payload)


@router.get("/{application_id}", response_model=ApplicationRead)
async def get_application(application_id: PydanticObjectId, user_id: CurrentUser) -> Application:
    return await service.get_application(user_id, application_id)
