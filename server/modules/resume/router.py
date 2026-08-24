from __future__ import annotations

from beanie import PydanticObjectId
from fastapi import APIRouter, HTTPException, status

from modules.resume import service
from modules.resume.models import ResumeRead, ResumeStore

router = APIRouter(tags=["resume"])


@router.post("", response_model=ResumeRead, status_code=status.HTTP_201_CREATED)
async def store_resume(payload: ResumeStore) -> ResumeRead:
    try:
        return ResumeRead.of(await service.store_resume(payload))
    except service.MatchNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except service.SelectionGateNotPassed as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except service.Fabrication as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.get("/{job_id}", response_model=ResumeRead)
async def get_resume(job_id: PydanticObjectId) -> ResumeRead:
    try:
        return ResumeRead.of(await service.get_resume(job_id))
    except service.ResumeNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/{job_id}/versions", response_model=list[ResumeRead])
async def list_versions(job_id: PydanticObjectId) -> list[ResumeRead]:
    return [ResumeRead.of(resume) for resume in await service.list_versions(job_id)]
