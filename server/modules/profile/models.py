from datetime import UTC, datetime

import pymongo
from beanie import Document, PydanticObjectId
from pydantic import BaseModel, EmailStr, Field


def _user_index() -> list[pymongo.IndexModel]:
    return [pymongo.IndexModel([("userId", pymongo.ASCENDING)])]


class Link(BaseModel):
    label: str
    value: str


class Project(BaseModel):
    name: str
    bullets: list[str] = Field(default_factory=list)


# --- personal details --------------------------------------------------------


class ProfileFields(BaseModel):
    name: str
    email: EmailStr
    headline: str | None = None
    phone: str | None = None
    location: str | None = None
    summary: str | None = None
    links: list[Link] = Field(default_factory=list)


class Profile(Document, ProfileFields):
    userId: PydanticObjectId
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "profile"
        # One profile per account, unlike the four lists below.
        indexes = [pymongo.IndexModel([("userId", pymongo.ASCENDING)], unique=True)]


class ProfileRead(ProfileFields):
    id: PydanticObjectId
    userId: PydanticObjectId


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


class Experience(Document, ExperienceFields):
    userId: PydanticObjectId
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "work_experience"
        indexes = _user_index()


class ExperienceRead(ExperienceFields):
    id: PydanticObjectId
    userId: PydanticObjectId


# --- education ---------------------------------------------------------------


class EducationFields(BaseModel):
    degree: str
    institution: str
    location: str | None = None
    start: str | None = None
    end: str | None = None
    note: str | None = None


class Education(Document, EducationFields):
    userId: PydanticObjectId
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "education"
        indexes = _user_index()


class EducationRead(EducationFields):
    id: PydanticObjectId
    userId: PydanticObjectId


# --- skills ------------------------------------------------------------------


class SkillFields(BaseModel):
    """One group and its items — `Languages: Python, Go`."""

    name: str
    items: list[str] = Field(default_factory=list)


class Skill(Document, SkillFields):
    userId: PydanticObjectId
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "skills"
        indexes = _user_index()


class SkillRead(SkillFields):
    id: PydanticObjectId
    userId: PydanticObjectId


# --- certifications ----------------------------------------------------------


class CertificationFields(BaseModel):
    name: str
    issuer: str
    year: str | None = None


class Certification(Document, CertificationFields):
    userId: PydanticObjectId
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "certifications"
        indexes = _user_index()


class CertificationRead(CertificationFields):
    id: PydanticObjectId
    userId: PydanticObjectId


# --- everything at once ------------------------------------------------------


class Resume(BaseModel):
    """The five collections for one user, assembled. What a template renders from.

    Holds the documents, not the `*Read` models: nothing serialises this to a
    response, and the services hand back documents.
    """

    profile: Profile
    experience: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    skills: list[Skill] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
