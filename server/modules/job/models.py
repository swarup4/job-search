from datetime import UTC, datetime
from enum import StrEnum

import pymongo
from beanie import Document, PydanticObjectId
from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class JobStatus(StrEnum):
    """Pipeline column on the dashboard board."""

    NEW = "new"
    REVIEWED = "reviewed"
    TAILORED = "tailored"
    APPLIED = "applied"
    ARCHIVED = "archived"


class JobSource(StrEnum):
    LINKEDIN = "linkedin"
    INDEED = "indeed"
    NAUKRI = "naukri"
    SERPAPI = "serpapi"
    CAREER_PAGE = "career_page"


class JobType(StrEnum):
    FULL_TIME = "full_time"
    CONTRACT = "contract"
    PART_TIME = "part_time"
    INTERNSHIP = "internship"


class WorkMode(StrEnum):
    ONSITE = "on_site"
    HYBRID = "hybrid"
    REMOTE = "remote"


# --- the posting -------------------------------------------------------------


class JobCreate(BaseModel):
    """What discovery posts. The prose goes to `job_descriptions`."""

    refId: str | None = None
    title: str
    company: str
    location: str
    jobType: JobType | None = None
    workMode: WorkMode | None = None
    experienceBand: str | None = None
    salaryText: str | None = None
    source: JobSource
    listingUrl: HttpUrl | None = None
    postedAt: datetime | None = None
    deadlineAt: datetime | None = None
    applicantCount: int | None = None
    dedupHash: str | None = None


class Job(Document):
    # The board's own id for this posting, when it exposes one.
    refId: str | None = None
    title: str
    company: str
    location: str
    jobType: JobType | None = None
    workMode: WorkMode | None = None
    experienceBand: str | None = None
    salaryText: str | None = None
    source: JobSource
    listingUrl: HttpUrl | None = None
    postedAt: datetime | None = None
    deadlineAt: datetime | None = None
    applicantCount: int | None = None
    # FR-1.4 — discovery hashes the normalized posting and refuses a repeat.
    dedupHash: str
    status: JobStatus = JobStatus.NEW
    shortlisted: bool = False
    discoveredAt: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "jobs"
        indexes = [
            pymongo.IndexModel([("dedupHash", pymongo.ASCENDING)], unique=True),
            # Every list and count is this shape: optionally one column, newest first.
            pymongo.IndexModel(
                [("status", pymongo.ASCENDING), ("discoveredAt", pymongo.DESCENDING)]
            ),
        ]


class JobUpdate(BaseModel):
    """Every field optional: a PATCH sends only what changed. The detail fields are
    what analysis reads out of the description when the board did not supply them."""

    status: JobStatus | None = None
    shortlisted: bool | None = None
    jobType: JobType | None = None
    workMode: WorkMode | None = None
    experienceBand: str | None = Field(default=None, max_length=60)
    salaryText: str | None = Field(default=None, max_length=80)


class JobRead(BaseModel):
    """`dedupHash` stays out — the dashboard never renders it."""

    # A response always carries every field, defaults included.
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    id: PydanticObjectId
    refId: str | None = None
    title: str
    company: str
    location: str
    jobType: JobType | None = None
    workMode: WorkMode | None = None
    experienceBand: str | None = None
    salaryText: str | None = None
    source: JobSource
    listingUrl: HttpUrl | None = None
    postedAt: datetime | None = None
    deadlineAt: datetime | None = None
    applicantCount: int | None = None
    status: JobStatus
    shortlisted: bool
    discoveredAt: datetime


class JobDescriptionPart(BaseModel):
    """The job's description as the details page needs it — the text, not the vector."""

    id: PydanticObjectId
    url: str
    pageTitle: str = ""
    jdText: str
    requirements: list[str] = Field(default_factory=list)
    links: list[str] = Field(default_factory=list)
    capturedAt: datetime


class JobDetailRead(BaseModel):
    """A job and its description in one read, for the Job Details page. `description`
    is null when the job has none stored."""

    # A response always carries every field, defaults included.
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    id: PydanticObjectId
    refId: str | None = None
    title: str
    company: str
    location: str
    jobType: JobType | None = None
    workMode: WorkMode | None = None
    experienceBand: str | None = None
    salaryText: str | None = None
    source: JobSource
    listingUrl: HttpUrl | None = None
    postedAt: datetime | None = None
    deadlineAt: datetime | None = None
    applicantCount: int | None = None
    status: JobStatus
    shortlisted: bool
    discoveredAt: datetime
    description: JobDescriptionPart | None = None


class JobCounts(BaseModel):
    """How many jobs sit in each pipeline column — the board's stat cards and column
    headers. Every status is present, zero included."""

    new: int = 0
    reviewed: int = 0
    tailored: int = 0
    applied: int = 0
    archived: int = 0


class JobCreated(BaseModel):
    """`duplicate` is how discovery learns its dedup hash already existed."""

    id: PydanticObjectId
    duplicate: bool
