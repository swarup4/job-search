import hashlib

from beanie import PydanticObjectId

from config.errors import NotFound
from modules.job_description.models import (
    DescriptionStatus,
    JobDescription,
    JobDescriptionCreate,
    JobDescriptionCreated,
    JobDescriptionUpdate,
)


class JobDescriptionNotFound(NotFound):
    def __init__(self, description_id: PydanticObjectId) -> None:
        super().__init__(f"job description {description_id} not found")


def compute_content_hash(payload: JobDescriptionCreate) -> str:
    """URL and text together, not text alone: the same boilerplate shell served by
    two postings is two descriptions, and a page recaptured after it changed is a
    new row rather than a silent overwrite. The fragment is dropped — `#apply` is
    the same page."""
    seed = f"{payload.url.split('#')[0]}|{payload.jdText}"
    return hashlib.sha256(seed.encode()).hexdigest()


async def create_description(payload: JobDescriptionCreate) -> JobDescriptionCreated:
    contentHash = payload.contentHash or compute_content_hash(payload)

    existing = await JobDescription.find_one(JobDescription.contentHash == contentHash)
    if existing is not None:
        # Recapturing an unchanged page is not an error — the extension says
        # "already captured" and the user carries on.
        return JobDescriptionCreated(id=existing.id, duplicate=True)

    description = JobDescription(
        **payload.model_dump(exclude={"contentHash"}),
        contentHash=contentHash,
        markdownLength=len(payload.jdText),
    )
    await description.insert()
    return JobDescriptionCreated(id=description.id, duplicate=False)


async def get_description(description_id: PydanticObjectId) -> JobDescription:
    description = await JobDescription.find_one(JobDescription.id == description_id)
    if description is None:
        raise JobDescriptionNotFound(description_id)
    return description


async def get_for_job(job_id: PydanticObjectId) -> JobDescription | None:
    """The description a job was parsed from, or None while it has none."""
    return await JobDescription.find_one(JobDescription.jobId == job_id)


async def list_descriptions(
    description_status: DescriptionStatus | None = None,
    url: str | None = None,
    limit: int = 50,
    skip: int = 0,
) -> list[JobDescription]:
    query: dict[str, object] = {}
    if description_status is not None:
        query["status"] = description_status
    if url:
        query["url"] = url

    return (
        await JobDescription.find(query)
        .sort(-JobDescription.capturedAt)
        .skip(skip)
        .limit(limit)
        .to_list()
    )


async def link_to_job(description_id: PydanticObjectId, job_id: PydanticObjectId) -> JobDescription:
    """Claim a capture as a posting's description. Parsing is what calls this."""
    description = await get_description(description_id)
    description.jobId = job_id
    description.status = DescriptionStatus.PARSED
    await description.save()
    return description


async def store_embedding(
    description_id: PydanticObjectId, embedding: list[float]
) -> JobDescription:
    description = await get_description(description_id)
    description.embedding = embedding
    await description.save()
    return description


async def set_status(description_id: PydanticObjectId, status: DescriptionStatus) -> JobDescription:
    """`discarded` is how a capture that turned out not to be a posting stops coming
    back in the parse queue."""
    description = await get_description(description_id)
    description.status = status
    await description.save()
    return description


async def update_description(
    description_id: PydanticObjectId, payload: JobDescriptionUpdate
) -> JobDescription:
    description = await get_description(description_id)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(description, field, value)
    await description.save()
    return description
