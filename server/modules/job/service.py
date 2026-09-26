import hashlib
from datetime import UTC, datetime

from beanie import PydanticObjectId

from config.errors import NotFound
from modules.job.models import (
    Job,
    JobCreate,
    JobCreated,
    JobDetailRead,
    JobUpdate,
)


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


def _query(company: str | None, exclude: list[PydanticObjectId] | None) -> dict[str, object]:
    query: dict[str, object] = {}
    if company:
        query["company"] = company
    if exclude:
        query["_id"] = {"$nin": exclude}
    return query


async def list_jobs(
    company: str | None = None,
    limit: int = 50,
    skip: int = 0,
    exclude: list[PydanticObjectId] | None = None,
) -> list[Job]:
    """Newest first. `exclude` is how another module asks for the jobs a user has not
    touched — the ones they applied to, or the ones already scored."""
    return (
        await Job.find(_query(company, exclude))
        .sort(-Job.discoveredAt)
        .skip(skip)
        .limit(limit)
        .to_list()
    )


async def count_jobs(exclude: list[PydanticObjectId] | None = None) -> int:
    return await Job.find(_query(None, exclude)).count()


async def get_job_detail(job_id: PydanticObjectId) -> JobDetailRead:
    """The job and its description in one query.

    This is the one place the job module reads another module's collection: a
    `$lookup` into `job_descriptions`, so the details page costs one round trip
    instead of two. The projection leaves out the embedding (~20 KB of floats) and
    the unused `htmlString`. A job with no description still comes back, with
    `description` null — "no description" is not "no job"."""
    rows = await Job.aggregate(
        [
            {"$match": {"_id": job_id}},
            {
                "$lookup": {
                    "from": "job_descriptions",
                    "localField": "_id",
                    "foreignField": "jobId",
                    "as": "description",
                    "pipeline": [
                        {
                            "$project": {
                                "_id": 0,
                                "id": "$_id",
                                "url": 1,
                                "pageTitle": 1,
                                "jdText": 1,
                                "requirements": 1,
                                "links": 1,
                                "capturedAt": 1,
                            }
                        }
                    ],
                }
            },
            {"$unwind": {"path": "$description", "preserveNullAndEmptyArrays": True}},
            {"$project": {"dedupHash": 0}},
        ]
    ).to_list()
    if not rows:
        raise JobNotFound(job_id)
    row = rows[0]
    row["id"] = row.pop("_id")
    return JobDetailRead(**row)


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
