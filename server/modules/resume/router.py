from __future__ import annotations

from beanie import PydanticObjectId
from fastapi import APIRouter, status

from modules.resume import service
from modules.resume.models import ResumeRead, ResumeStore, TailoredResume

router = APIRouter(tags=["resume"])


@router.post("", response_model=ResumeRead, status_code=status.HTTP_201_CREATED)
async def store_resume(payload: ResumeStore) -> TailoredResume:
    return await service.store_resume(payload)


@router.get("/{job_id}", response_model=ResumeRead)
async def get_resume(job_id: PydanticObjectId) -> TailoredResume:
    return await service.get_resume(job_id)


@router.get("/{job_id}/versions", response_model=list[ResumeRead])
async def list_versions(job_id: PydanticObjectId) -> list[TailoredResume]:
    return await service.list_versions(job_id)
