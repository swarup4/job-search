from beanie import PydanticObjectId
from fastapi import APIRouter, Query, status

from modules.account import CurrentUser
from modules.job import service
from modules.job.models import (
    Job,
    JobCounts,
    JobCreate,
    JobCreated,
    JobDetailRead,
    JobRead,
    JobStatus,
    JobUpdate,
)

router = APIRouter(tags=["job"])


@router.get("", response_model=list[JobRead])
async def list_jobs(
    _: CurrentUser,
    job_status: JobStatus | None = Query(default=None, alias="status"),
    shortlisted: bool | None = None,
    company: str | None = None,
    limit: int = Query(default=50, le=200),
    skip: int = 0,
) -> list[Job]:
    return await service.list_jobs(job_status, shortlisted, company, limit, skip)


@router.get("/counts", response_model=JobCounts)
async def count_jobs(_: CurrentUser) -> JobCounts:
    return await service.count_by_status()


@router.post("/createJob", response_model=JobCreated, status_code=status.HTTP_201_CREATED)
async def create_job(payload: JobCreate, _: CurrentUser) -> JobCreated:
    return await service.create_job(payload)


@router.get("/getJob/{job_id}", response_model=JobRead)
async def get_job(job_id: PydanticObjectId, _: CurrentUser) -> Job:
    return await service.get_job(job_id)


@router.get("/getJobDetails/{job_id}", response_model=JobDetailRead)
async def get_job_details(job_id: PydanticObjectId, _: CurrentUser) -> JobDetailRead:
    return await service.get_job_detail(job_id)


@router.patch("/updateJob/{job_id}", response_model=JobRead)
async def update_job(job_id: PydanticObjectId, payload: JobUpdate, _: CurrentUser) -> Job:
    return await service.update_job(job_id, payload)
