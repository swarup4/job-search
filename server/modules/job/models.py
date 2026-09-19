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
    """Every field optional: a PATCH sends only what changed."""

    status: JobStatus | None = None


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


class JobCreated(BaseModel):
    """`duplicate` is how discovery learns its dedup hash already existed."""

    id: PydanticObjectId
    duplicate: bool
