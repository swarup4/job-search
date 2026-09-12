from beanie import PydanticObjectId
from fastapi import APIRouter, Query, status

from modules.account import CurrentUser
from modules.job import service
from modules.job.models import Job, JobCreate, JobCreated, JobRead, JobStatus, JobUpdate

router = APIRouter(tags=["job"])


@router.get("", response_model=list[JobRead])
async def list_jobs(
    user_id: CurrentUser,
    job_status: JobStatus | None = Query(default=None, alias="status"),
    shortlisted: bool | None = None,
    company: str | None = None,
    limit: int = Query(default=50, le=200),
    skip: int = 0,
) -> list[Job]:
    return await service.list_jobs(user_id, job_status, shortlisted, company, limit, skip)


@router.post("", response_model=JobCreated, status_code=status.HTTP_201_CREATED)
async def create_job(payload: JobCreate, user_id: CurrentUser) -> JobCreated:
    return await service.create_job(user_id, payload)


@router.get("/{job_id}", response_model=JobRead)
async def get_job(job_id: PydanticObjectId, user_id: CurrentUser) -> Job:
    return await service.get_job(user_id, job_id)


@router.patch("/{job_id}", response_model=JobRead)
async def update_job(job_id: PydanticObjectId, payload: JobUpdate, user_id: CurrentUser) -> Job:
    return await service.update_job(user_id, job_id, payload)
