from datetime import UTC, datetime

import pymongo
from beanie import Document, PydanticObjectId
from pydantic import BaseModel, ConfigDict, Field


class LineChange(BaseModel):
    """One tailored line of the .tex, kept with what it replaced so the diff
    screen and the source screen can never disagree."""

    lineNo: int = Field(ge=1)
    text: str
    previous: str | None = None


class ResumeStore(BaseModel):
    """What the tailoring agent posts once it has written the file."""

    jobId: PydanticObjectId
    filePath: str
    templatePath: str = "templates/base_resume.tex"
    incorporated: list[str] = Field(default_factory=list)
    declined: list[str] = Field(default_factory=list)
    changes: list[LineChange] = Field(default_factory=list)


class TailoredResume(Document):
    """FR-4.4 — a .tex path and the selection set that produced it. No PDF in v1."""

    userId: PydanticObjectId
    jobId: PydanticObjectId
    matchId: PydanticObjectId
    filePath: str
    templatePath: str = "templates/base_resume.tex"
    incorporated: list[str] = Field(default_factory=list)
    declined: list[str] = Field(default_factory=list)
    changes: list[LineChange] = Field(default_factory=list)
    version: int = Field(default=1, ge=1)

    # The audit trail NFR-8 requires: every changed line traces back to these.
    selectedKeys: list[str] = Field(default_factory=list)

    renderedAt: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "resumes"
        indexes = [
            pymongo.IndexModel(
                [("jobId", pymongo.ASCENDING), ("version", pymongo.DESCENDING)], unique=True
            ),
        ]


class ResumeRead(BaseModel):
    # A response always carries every field, defaults included.
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    id: PydanticObjectId
    jobId: PydanticObjectId
    matchId: PydanticObjectId
    filePath: str
    templatePath: str = "templates/base_resume.tex"
    incorporated: list[str] = Field(default_factory=list)
    declined: list[str] = Field(default_factory=list)
    changes: list[LineChange] = Field(default_factory=list)
    version: int
    selectedKeys: list[str]
    renderedAt: datetime


class BaseResumeStore(BaseModel):
    """What the Resume screen submits once the user accepts the render."""

    templateId: PydanticObjectId
    tex: str = Field(min_length=1)


class BaseResume(Document):
    """The user's default resume: the template they prefer, and the .tex it produced.

    The source is kept verbatim rather than re-rendered on read, so the document a
    tailoring run starts from is the one the user actually approved — later edits to
    the profile or the template cannot rewrite it behind their back.
    """

    userId: PydanticObjectId
    templateId: PydanticObjectId
    templateName: str
    tex: str
    createdAt: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "base_resumes"
        indexes = [
            pymongo.IndexModel([("userId", pymongo.ASCENDING)], unique=True),
        ]


class BaseResumeRead(BaseModel):
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    id: PydanticObjectId
    templateId: PydanticObjectId
    templateName: str
    tex: str
    createdAt: datetime
    updatedAt: datetime
