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


class Company(BaseModel):
    """Denormalized onto the job — the company rail on the job page reads only this."""

    name: str
    industry: str | None = None
    size: str | None = None
    founded: int | None = None
    site: str | None = None
    blurb: str | None = None


class JobCreate(BaseModel):
    """The posting as discovery found it."""

    title: str
    company: Company
    location: str
    jobType: JobType | None = None
    workMode: WorkMode | None = None
    experienceBand: str | None = None
    salaryText: str | None = None
    summary: str | None = None
    responsibilities: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    source: JobSource
    sourceUrl: HttpUrl | None = None
    postedAt: datetime | None = None
    deadlineAt: datetime | None = None
    applicantCount: int | None = None
    jdText: str
    dedupHash: str | None = None


class Job(Document):
    # The account this job belongs to. Every query filters on it, so one user's
    # board never shows another's postings.
    userId: PydanticObjectId

    title: str
    company: Company
    location: str
    jobType: JobType | None = None
    workMode: WorkMode | None = None
    experienceBand: str | None = None
    salaryText: str | None = None
    summary: str | None = None
    responsibilities: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    source: JobSource
    sourceUrl: HttpUrl | None = None
    postedAt: datetime | None = None
    deadlineAt: datetime | None = None
    applicantCount: int | None = None

    jdText: str
    # FR-1.4 — discovery hashes the normalized posting and refuses a repeat.
    dedupHash: str

    status: JobStatus = JobStatus.NEW
    shortlisted: bool = False
    discoveredAt: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "jobs"
        indexes = [
            # Unique per user, not globally: the same posting found by two people is
            # two rows, and one user's discovery must not silently dedup another's.
            pymongo.IndexModel(
                [("userId", pymongo.ASCENDING), ("dedupHash", pymongo.ASCENDING)], unique=True
            ),
            pymongo.IndexModel(
                [
                    ("userId", pymongo.ASCENDING),
                    ("status", pymongo.ASCENDING),
                    ("discoveredAt", pymongo.DESCENDING),
                ]
            ),
            pymongo.IndexModel([("userId", pymongo.ASCENDING), ("shortlisted", pymongo.ASCENDING)]),
            pymongo.IndexModel(
                [("userId", pymongo.ASCENDING), ("company.name", pymongo.ASCENDING)]
            ),
            pymongo.IndexModel([("title", pymongo.TEXT), ("jdText", pymongo.TEXT)]),
        ]


class JobUpdate(BaseModel):
    """Every field optional: a PATCH sends only what changed."""

    status: JobStatus | None = None
    shortlisted: bool | None = None
    summary: str | None = None
    responsibilities: list[str] | None = None
    requirements: list[str] | None = None


class JobRead(BaseModel):
    """`jdText` and `dedupHash` stay out — the dashboard never renders either."""

    # A response always carries every field, defaults included.
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    id: PydanticObjectId
    title: str
    company: Company
    location: str
    jobType: JobType | None = None
    workMode: WorkMode | None = None
    experienceBand: str | None = None
    salaryText: str | None = None
    summary: str | None = None
    responsibilities: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    source: JobSource
    sourceUrl: HttpUrl | None = None
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
