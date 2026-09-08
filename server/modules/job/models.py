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


class JobContent(BaseModel):
    """The posting as discovery found it. Shared by the document and both payloads,
    so a field is declared once."""

    title: str
    company: Company
    location: str
    job_type: JobType | None = None
    work_mode: WorkMode | None = None
    experience_band: str | None = None
    salary_text: str | None = None

    summary: str | None = None
    responsibilities: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)

    source: JobSource
    source_url: HttpUrl | None = None
    posted_at: datetime | None = None
    deadline_at: datetime | None = None
    applicant_count: int | None = None


class Job(Document, JobContent):
    jd_text: str

    # FR-1.4 — discovery hashes the normalized posting and refuses a repeat.
    dedup_hash: str

    status: JobStatus = JobStatus.NEW
    shortlisted: bool = False
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "jobs"
        indexes = [
            pymongo.IndexModel([("dedup_hash", pymongo.ASCENDING)], unique=True),
            pymongo.IndexModel(
                [("status", pymongo.ASCENDING), ("discovered_at", pymongo.DESCENDING)]
            ),
            pymongo.IndexModel([("shortlisted", pymongo.ASCENDING)]),
            pymongo.IndexModel([("company.name", pymongo.ASCENDING)]),
            pymongo.IndexModel([("title", pymongo.TEXT), ("jd_text", pymongo.TEXT)]),
        ]


class JobCreate(JobContent):
    jd_text: str
    dedup_hash: str | None = None


class JobUpdate(BaseModel):
    status: JobStatus | None = None
    shortlisted: bool | None = None
    summary: str | None = None
    responsibilities: list[str] | None = None
    requirements: list[str] | None = None


class JobRead(JobContent):
    """`jd_text` and `dedup_hash` stay out — the dashboard never renders either."""

    # Responses always carry every field; inheriting a default must not
    # make it optional in the schema.
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    id: PydanticObjectId
    status: JobStatus
    shortlisted: bool
    discovered_at: datetime


class JobCreated(BaseModel):
    """`duplicate` is how discovery learns its dedup hash already existed."""

    id: PydanticObjectId
    duplicate: bool
