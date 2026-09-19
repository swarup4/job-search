import hashlib
from datetime import UTC, datetime

from beanie import PydanticObjectId

from config.errors import NotFound
from modules.job.models import Job, JobCreate, JobCreated, JobStatus, JobUpdate


class JobNotFound(NotFound):
    def __init__(self, job_id: PydanticObjectId) -> None:
        super().__init__(f"job {job_id} not found")


def compute_dedup_hash(payload: JobCreate) -> str:
    """FR-1.4 — the same posting from two boards must collapse to one row.

    A board's own id is the strongest signal, so it wins when there is one. The JD
    prose used to be part of this seed and no longer can be — it lives in
    `job_descriptions`, which is written after the job exists."""
    if payload.refId:
        seed = f"{payload.source}|{payload.refId}".lower()
    else:
        seed = "|".join(
            part.strip().lower() for part in (payload.title, payload.company, payload.location)
        )
    return hashlib.sha256(seed.encode()).hexdigest()


async def create_job(payload: JobCreate) -> JobCreated:
    dedupHash = payload.dedupHash or compute_dedup_hash(payload)

    existing = await Job.find_one(Job.dedupHash == dedupHash)
    if existing is not None:
        return JobCreated(id=existing.id, duplicate=True)

    job = Job(**payload.model_dump(exclude={"dedupHash"}), dedupHash=dedupHash)
    await job.insert()
    return JobCreated(id=job.id, duplicate=False)


async def get_job(job_id: PydanticObjectId) -> Job:
    job = await Job.find_one(Job.id == job_id)
    if job is None:
        raise JobNotFound(job_id)
    return job


async def list_jobs(
    status: JobStatus | None = None,
    shortlisted: bool | None = None,
    company: str | None = None,
    limit: int = 50,
    skip: int = 0,
) -> list[Job]:
    query: dict[str, object] = {}
    if status is not None:
        query["status"] = status
    if shortlisted is not None:
        query["shortlisted"] = shortlisted
    if company:
        query["company"] = company
    return await Job.find(query).sort(-Job.discoveredAt).skip(skip).limit(limit).to_list()


async def count_jobs(status: JobStatus | None = None) -> int:
    query: dict[str, object] = {}
    if status:
        query["status"] = status
    return await Job.find(query).count()


async def update_job(job_id: PydanticObjectId, payload: JobUpdate) -> Job:
    job = await get_job(job_id)
    changes = payload.model_dump(exclude_none=True)
    if not changes:
        return job

    for field, value in changes.items():
        setattr(job, field, value)
    job.updatedAt = datetime.now(UTC)
    await job.save()
    return job
