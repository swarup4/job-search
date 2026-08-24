from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

import pymongo
from beanie import Document, PydanticObjectId
from pydantic import BaseModel, EmailStr, Field

# --- resume material ---------------------------------------------------------


class ProfileLink(BaseModel):
    label: str
    value: str


class Personal(BaseModel):
    name: str
    headline: str | None = None  # scoring context only; never written into the .tex
    phone: str | None = None
    location: str | None = None
    links: list[ProfileLink] = Field(default_factory=list)


class Experience(BaseModel):
    key: str
    title: str
    company: str
    location: str | None = None
    start: str
    end: str | None = None
    current: bool = False
    bullets: list[str] = Field(default_factory=list)


class Education(BaseModel):
    key: str
    degree: str
    institution: str
    location: str | None = None
    start: str | None = None
    end: str | None = None
    note: str | None = None


class SkillGroup(BaseModel):
    """Maps one-to-one onto a \\skillrow in the template."""

    name: str
    items: list[str] = Field(default_factory=list)


class Certification(BaseModel):
    key: str
    name: str
    issuer: str
    year: str | None = None


# --- preferences (the Settings screen) ---------------------------------------


class TargetPreferences(BaseModel):
    roles: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    work_mode: str | None = None
    min_experience: int | None = None
    max_experience: int | None = None
    min_salary: str | None = None


class CompanySize(BaseModel):
    label: str
    on: bool = False


class CompanyPreferences(BaseModel):
    preferred: list[str] = Field(default_factory=list)
    excluded: list[str] = Field(default_factory=list)
    sizes: list[CompanySize] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)
    avoid_staffing: bool = False


class DiscoverySource(BaseModel):
    name: str
    on: bool = True
    found: int = 0


class DiscoveryPreferences(BaseModel):
    schedule_cron: str = "0 6 * * *"
    min_match: int = Field(default=70, ge=0, le=100)
    dedupe: bool = True
    # FR-1.3. The Settings screen renders this toggle disabled for the same reason.
    respect_robots: Literal[True] = True
    sources: list[DiscoverySource] = Field(default_factory=list)


class ApplicationPreferences(BaseModel):
    follow_up_days: int = Field(default=5, ge=1)
    sheet_sync: bool = False
    sheet_name: str | None = None
    # FR-5.3 / NFR-7 — typed shut, not defaulted off. There is no value to set.
    auto_submit: Literal[False] = False


class AIPreferences(BaseModel):
    """Names only. Endpoints and keys live in each tier's own settings, never here."""

    llm: str = "qwen2.5:32b"
    llm_host: str = "http://localhost:11434"
    embed_model: str | None = None
    rerank: bool = True
    judge: str = "local (Ollama)"


class Preferences(BaseModel):
    targets: TargetPreferences = Field(default_factory=TargetPreferences)
    company: CompanyPreferences = Field(default_factory=CompanyPreferences)
    discovery: DiscoveryPreferences = Field(default_factory=DiscoveryPreferences)
    applications: ApplicationPreferences = Field(default_factory=ApplicationPreferences)
    ai: AIPreferences = Field(default_factory=AIPreferences)


# --- documents ---------------------------------------------------------------


class Profile(Document):
    """Single-user by design (PRD §4). `email` is the profile's key."""

    email: EmailStr  # mandatory — a resume without a contact address is not sendable

    personal: Personal
    summary: str | None = None
    experience: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    skill_groups: list[SkillGroup] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)

    preferences: Preferences = Field(default_factory=Preferences)

    resume_template_path: str = "templates/base_resume.tex"
    last_indexed_at: datetime | None = None
    chunk_count: int = 0
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "profile"
        indexes = [pymongo.IndexModel([("email", pymongo.ASCENDING)], unique=True)]


class ResumeChunkText(Document):
    """The local half of the RAG pair. Atlas holds the vector for this chunk_id
    and nothing else — text at rest never leaves the machine (rag-pipeline.md)."""

    chunk_id: str
    section: str
    text: str
    source_ref: str | None = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "resume_chunk_text"
        indexes = [
            pymongo.IndexModel([("chunk_id", pymongo.ASCENDING)], unique=True),
            pymongo.IndexModel([("section", pymongo.ASCENDING)]),
        ]


class ProfileCreate(BaseModel):
    """Creating a profile requires an email — there is no blank starting state."""

    email: EmailStr
    personal: Personal
    summary: str | None = None
    experience: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    skill_groups: list[SkillGroup] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
    preferences: Preferences = Field(default_factory=Preferences)
    resume_template_path: str = "templates/base_resume.tex"


class ProfileUpdate(BaseModel):
    email: EmailStr | None = None
    personal: Personal | None = None
    summary: str | None = None
    experience: list[Experience] | None = None
    education: list[Education] | None = None
    skill_groups: list[SkillGroup] | None = None
    certifications: list[Certification] | None = None
    preferences: Preferences | None = None
    resume_template_path: str | None = None


class ChunkWrite(BaseModel):
    chunk_id: str
    section: str
    text: str
    source_ref: str | None = None


class ProfileRead(BaseModel):
    id: PydanticObjectId
    email: EmailStr
    personal: Personal
    summary: str | None
    experience: list[Experience]
    education: list[Education]
    skill_groups: list[SkillGroup]
    certifications: list[Certification]
    preferences: Preferences
    resume_template_path: str
    last_indexed_at: datetime | None
    chunk_count: int

    @classmethod
    def of(cls, profile: Profile) -> ProfileRead:
        return cls(id=profile.id, **profile.model_dump(exclude={"id", "updated_at"}))
