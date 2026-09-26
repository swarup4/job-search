from beanie import PydanticObjectId
from fastapi import APIRouter, Query, status

from modules.account import CurrentUser
from modules.job_description import service
from modules.job_description.models import (
    DescriptionStatus,
    EmbeddingWrite,
    JobDescription,
    JobDescriptionCreate,
    JobDescriptionCreated,
    JobDescriptionDetail,
    JobDescriptionRead,
    JobDescriptionUpdate,
)

router = APIRouter(tags=["job-description"])


@router.get("", response_model=list[JobDescriptionRead])
async def list_descriptions(
    _: CurrentUser,
    description_status: DescriptionStatus | None = Query(default=None, alias="status"),
    url: str | None = None,
    limit: int = Query(default=50, le=200),
    skip: int = 0,
) -> list[JobDescription]:
    return await service.list_descriptions(description_status, url, limit, skip)


@router.post("", response_model=JobDescriptionCreated, status_code=status.HTTP_201_CREATED)
async def create_description(
    payload: JobDescriptionCreate, _: CurrentUser
) -> JobDescriptionCreated:
    return await service.create_description(payload)


@router.get("/for-job/{job_id}", response_model=JobDescriptionDetail | None)
async def get_for_job(job_id: PydanticObjectId, _: CurrentUser) -> JobDescription | None:
    return await service.get_for_job(job_id)


@router.post("/link/{description_id}/{job_id}", response_model=JobDescriptionRead)
async def link_to_job(
    description_id: PydanticObjectId, job_id: PydanticObjectId, _: CurrentUser
) -> JobDescription:
    return await service.link_to_job(description_id, job_id)


@router.patch("/status/{description_id}", response_model=JobDescriptionRead)
async def set_status(
    description_id: PydanticObjectId, new_status: DescriptionStatus, _: CurrentUser
) -> JobDescription:
    return await service.set_status(description_id, new_status)


@router.put("/embedding/{description_id}", response_model=JobDescriptionRead)
async def store_embedding(
    description_id: PydanticObjectId, payload: EmbeddingWrite, _: CurrentUser
) -> JobDescription:
    return await service.store_embedding(description_id, payload.embedding)


@router.patch("/{description_id}", response_model=JobDescriptionRead)
async def update_description(
    description_id: PydanticObjectId, payload: JobDescriptionUpdate, _: CurrentUser
) -> JobDescription:
    return await service.update_description(description_id, payload)


@router.get("/{description_id}", response_model=JobDescriptionDetail)
async def get_description(description_id: PydanticObjectId, _: CurrentUser) -> JobDescription:
    return await service.get_description(description_id)
