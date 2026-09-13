from datetime import UTC, datetime

import pymongo
from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field

from modules.account import Account


class Link(BaseModel):
    label: str
    value: str


class Project(BaseModel):
    name: str
    bullets: list[str] = Field(default_factory=list)


# --- personal details --------------------------------------------------------


class ProfileFields(BaseModel):
    headline: str | None = None
    phone: str | None = None
    location: str | None = None
    summary: str | None = None
    links: list[Link] = Field(default_factory=list)


class Profile(Document):
    userId: PydanticObjectId
    headline: str | None = None
    phone: str | None = None
    location: str | None = None
    summary: str | None = None
    links: list[Link] = Field(default_factory=list)
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "profile"
        indexes = [pymongo.IndexModel([("userId", pymongo.ASCENDING)], unique=True)]


class ProfileRead(BaseModel):
    id: PydanticObjectId
    userId: PydanticObjectId
    headline: str | None = None
    phone: str | None = None
    location: str | None = None
    summary: str | None = None
    links: list[Link] = Field(default_factory=list)


# --- work experience ---------------------------------------------------------


class ExperienceFields(BaseModel):
    title: str
    company: str
    location: str | None = None
    start: str
    end: str | None = None
    current: bool = False
    bullets: list[str] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)


class Experience(Document):
    userId: PydanticObjectId
    title: str
    company: str
    location: str | None = None
    start: str
    end: str | None = None
    current: bool = False
    bullets: list[str] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "work_experience"
        indexes = [pymongo.IndexModel([("userId", pymongo.ASCENDING)])]


class ExperienceRead(BaseModel):
    id: PydanticObjectId
    userId: PydanticObjectId
    title: str
    company: str
    location: str | None = None
    start: str
    end: str | None = None
    current: bool = False
    bullets: list[str] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)


# --- education ---------------------------------------------------------------

class EducationFields(BaseModel):
    degree: str
    institution: str
    location: str | None = None
    start: str | None = None
    end: str | None = None
    note: str | None = None


class Education(Document):
    userId: PydanticObjectId
    degree: str
    institution: str
    location: str | None = None
    start: str | None = None
    end: str | None = None
    note: str | None = None
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "education"
        indexes = [pymongo.IndexModel([("userId", pymongo.ASCENDING)])]


class EducationRead(BaseModel):
    id: PydanticObjectId
    userId: PydanticObjectId
    degree: str
    institution: str
    location: str | None = None
    start: str | None = None
    end: str | None = None
    note: str | None = None


# --- skills ------------------------------------------------------------------

class SkillFields(BaseModel):
    """One group and its items — `Languages: Python, Go`."""

    name: str
    items: list[str] = Field(default_factory=list)


class Skill(Document):
    userId: PydanticObjectId
    name: str
    items: list[str] = Field(default_factory=list)
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "skills"
        indexes = [pymongo.IndexModel([("userId", pymongo.ASCENDING)])]


class SkillRead(BaseModel):
    id: PydanticObjectId
    userId: PydanticObjectId
    name: str
    items: list[str] = Field(default_factory=list)


# --- certifications ----------------------------------------------------------


class CertificationFields(BaseModel):
    name: str
    issuer: str
    year: str | None = None


class Certification(Document):
    userId: PydanticObjectId
    name: str
    issuer: str
    year: str | None = None
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "certifications"
        indexes = [pymongo.IndexModel([("userId", pymongo.ASCENDING)])]


class CertificationRead(BaseModel):
    id: PydanticObjectId
    userId: PydanticObjectId
    name: str
    issuer: str
    year: str | None = None


# --- everything at once ------------------------------------------------------


class Resume(BaseModel):
    """What a template renders from: the account, for the name and email it owns,
    plus the five profile collections."""

    account: Account
    profile: Profile
    experience: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    skills: list[Skill] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
