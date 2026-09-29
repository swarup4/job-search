from beanie import PydanticObjectId
from fastapi import APIRouter, status

from modules.account import CurrentUser
from modules.job import service
from modules.job.models import (
    Job,
    JobCreate,
    JobCreated,
    JobDetailRead,
    JobRead,
    JobSearch,
    JobSearchResult,
    JobUpdate,
)

router = APIRouter(tags=["job"])


@router.post("/search", response_model=JobSearchResult)
async def search_jobs(filters: JobSearch, user_id: CurrentUser) -> JobSearchResult:
    return await service.search_jobs(user_id, filters)


@router.post("/createJob", response_model=JobCreated, status_code=status.HTTP_201_CREATED)
async def create_job(payload: JobCreate, _: CurrentUser) -> JobCreated:
    return await service.create_job(payload)


@router.get("/getJob/{job_id}", response_model=JobRead)
async def get_job(job_id: PydanticObjectId, _: CurrentUser) -> Job:
    return await service.get_job(job_id)


@router.get("/getJobDetails/{job_id}", response_model=JobDetailRead)
async def get_job_details(job_id: PydanticObjectId, user_id: CurrentUser) -> JobDetailRead:
    return await service.get_job_detail(job_id, user_id)


@router.patch("/updateJob/{job_id}", response_model=JobRead)
async def update_job(job_id: PydanticObjectId, payload: JobUpdate, _: CurrentUser) -> Job:
    return await service.update_job(job_id, payload)
