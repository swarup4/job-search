from datetime import UTC, datetime

import pymongo
from beanie import Document, PydanticObjectId
from pydantic import BaseModel, EmailStr, Field


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


class ProfileUpdate(BaseModel):
    """A PATCH body: only the fields the caller sent are touched. Distinguishing
    "absent" from "null" is the point — an explicit null clears the field, which
    `exclude_unset` preserves and `exclude_none` would swallow.

    `links` is all-or-nothing: half a list means nothing, so sending it replaces it."""

    headline: str | None = None
    phone: str | None = None
    location: str | None = None
    summary: str | None = None
    links: list[Link] | None = None


class Profile(Document):
    userId: PydanticObjectId
    headline: str | None = None
    phone: str | None = None
    location: str | None = None
    summary: str | None = None
    links: list[Link] = Field(default_factory=list)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(UTC))
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
    createdAt: datetime = Field(default_factory=lambda: datetime.now(UTC))
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


class Education(Document):
    userId: PydanticObjectId
    degree: str
    institution: str
    location: str | None = None
    start: str | None = None
    end: str | None = None
    createdAt: datetime = Field(default_factory=lambda: datetime.now(UTC))
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


# --- skills ------------------------------------------------------------------

class SkillFields(BaseModel):
    """One group and its items — `Languages: Python, Go`."""

    name: str
    items: list[str] = Field(default_factory=list)


class Skill(Document):
    userId: PydanticObjectId
    name: str
    items: list[str] = Field(default_factory=list)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(UTC))
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
    createdAt: datetime = Field(default_factory=lambda: datetime.now(UTC))
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


class UserProfile(BaseModel):
    """Everything keyed to one account. Answers `GET /profile/getProfile`, and is what
    a template renders from.

    `profile` is null until personal details are saved. The four lists do not wait for
    it — each is keyed by `userId` on its own — so they can be filled in first.
    """

    id: PydanticObjectId
    name: str
    email: EmailStr
    role: str = ""
    profilePicture: str | None = None
    profile: ProfileRead | None = None
    work: list[ExperienceRead] = Field(default_factory=list)
    education: list[EducationRead] = Field(default_factory=list)
    skill: list[SkillRead] = Field(default_factory=list)
    certification: list[CertificationRead] = Field(default_factory=list)
