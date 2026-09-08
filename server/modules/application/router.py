from beanie import PydanticObjectId
from fastapi import APIRouter, Query, status

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


@router.get("", response_model=list[ApplicationRead])
async def list_applications(
    application_status: ApplicationStatus | None = Query(default=None, alias="status"),
) -> list[Application]:
    return await service.list_applications(application_status)


@router.post("", response_model=ApplicationRead, status_code=status.HTTP_201_CREATED)
async def stage_application(payload: ApplicationStage) -> Application:
    return await service.stage_application(payload)


@router.get("/answer-bank", response_model=list[AnswerBank])
async def answer_bank() -> list[AnswerBank]:
    """Read by the extension's background worker for screening questions."""
    return await service.list_answer_bank()


@router.get("/for-job/{job_id}", response_model=ApplicationRead | None)
async def get_for_job(job_id: PydanticObjectId) -> Application | None:
    return await service.get_for_job(job_id)


@router.get("/{application_id}", response_model=ApplicationRead)
async def get_application(application_id: PydanticObjectId) -> Application:
    return await service.get_application(application_id)


@router.post("/{application_id}/fill", response_model=ApplicationRead)
async def record_fill(application_id: PydanticObjectId, payload: ApplicationFill) -> Application:
    return await service.record_fill(application_id, payload)


@router.patch("/{application_id}/status", response_model=ApplicationRead)
async def set_status(application_id: PydanticObjectId, payload: StatusTransition) -> Application:
    return await service.set_status(application_id, payload)
