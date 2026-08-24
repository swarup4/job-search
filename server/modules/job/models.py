from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

import pymongo
from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field, HttpUrl


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


class Job(Document):
    title: str
    company: Company
    location: str
    job_type: JobType | None = None
    work_mode: WorkMode | None = None
    experience_band: str | None = None
    salary_text: str | None = None

    jd_text: str
    summary: str | None = None
    responsibilities: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)

    source: JobSource
    source_url: HttpUrl | None = None
    posted_at: datetime | None = None
    deadline_at: datetime | None = None
    applicant_count: int | None = None

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


class JobCreate(BaseModel):
    title: str
    company: Company
    location: str
    jd_text: str
    source: JobSource
    job_type: JobType | None = None
    work_mode: WorkMode | None = None
    experience_band: str | None = None
    salary_text: str | None = None
    summary: str | None = None
    responsibilities: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    source_url: HttpUrl | None = None
    posted_at: datetime | None = None
    deadline_at: datetime | None = None
    applicant_count: int | None = None
    dedup_hash: str | None = None


class JobUpdate(BaseModel):
    status: JobStatus | None = None
    shortlisted: bool | None = None
    summary: str | None = None
    responsibilities: list[str] | None = None
    requirements: list[str] | None = None


class JobRead(BaseModel):
    id: PydanticObjectId = Field(serialization_alias="id")
    title: str
    company: Company
    location: str
    job_type: JobType | None
    work_mode: WorkMode | None
    experience_band: str | None
    salary_text: str | None
    summary: str | None
    responsibilities: list[str]
    requirements: list[str]
    source: JobSource
    source_url: HttpUrl | None
    posted_at: datetime | None
    deadline_at: datetime | None
    applicant_count: int | None
    status: JobStatus
    shortlisted: bool
    discovered_at: datetime

    @classmethod
    def of(cls, job: Job) -> JobRead:
        return cls(
            id=job.id, **job.model_dump(exclude={"id", "jd_text", "dedup_hash", "updated_at"})
        )


class JobCreated(BaseModel):
    """`duplicate` is how discovery learns its dedup hash already existed."""

    id: PydanticObjectId
    duplicate: bool
