from __future__ import annotations

from datetime import UTC, datetime

import pymongo
from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field


class LineChange(BaseModel):
    """One tailored line of the .tex, kept with what it replaced so the diff
    screen and the source screen can never disagree."""

    line_no: int = Field(ge=1)
    text: str
    previous: str | None = None


class TailoredResume(Document):
    """FR-4.4 — a .tex path and the selection set that produced it. No PDF in v1."""

    job_id: PydanticObjectId
    match_id: PydanticObjectId

    version: int = Field(default=1, ge=1)
    file_path: str
    template_path: str = "templates/base_resume.tex"

    # The audit trail NFR-8 requires: every line above traces back to these.
    selected_keys: list[str] = Field(default_factory=list)
    incorporated: list[str] = Field(default_factory=list)
    declined: list[str] = Field(default_factory=list)
    changes: list[LineChange] = Field(default_factory=list)

    rendered_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "resumes"
        indexes = [
            pymongo.IndexModel(
                [("job_id", pymongo.ASCENDING), ("version", pymongo.DESCENDING)], unique=True
            ),
        ]


class ResumeStore(BaseModel):
    """What the tailoring agent posts once it has written the file."""

    job_id: PydanticObjectId
    file_path: str
    incorporated: list[str] = Field(default_factory=list)
    declined: list[str] = Field(default_factory=list)
    changes: list[LineChange] = Field(default_factory=list)
    template_path: str = "templates/base_resume.tex"


class ResumeRead(BaseModel):
    id: PydanticObjectId
    job_id: PydanticObjectId
    match_id: PydanticObjectId
    version: int
    file_path: str
    template_path: str
    selected_keys: list[str]
    incorporated: list[str]
    declined: list[str]
    changes: list[LineChange]
    rendered_at: datetime

    @classmethod
    def of(cls, resume: TailoredResume) -> ResumeRead:
        return cls(id=resume.id, **resume.model_dump(exclude={"id"}))
