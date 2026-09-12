from beanie import PydanticObjectId
from fastapi import APIRouter, status

from modules.account import CurrentUser
from modules.resume import service
from modules.resume.models import ResumeRead, ResumeStore, TailoredResume

router = APIRouter(tags=["resume"])


@router.get("/versions/{job_id}", response_model=list[ResumeRead])
async def list_versions(job_id: PydanticObjectId, user_id: CurrentUser) -> list[TailoredResume]:
    return await service.list_versions(user_id, job_id)


@router.post("", response_model=ResumeRead, status_code=status.HTTP_201_CREATED)
async def store_resume(payload: ResumeStore, user_id: CurrentUser) -> TailoredResume:
    return await service.store_resume(user_id, payload)


@router.get("/{job_id}", response_model=ResumeRead)
async def get_resume(job_id: PydanticObjectId, user_id: CurrentUser) -> TailoredResume:
    return await service.get_resume(user_id, job_id)
