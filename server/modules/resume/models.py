from datetime import UTC, datetime

import pymongo
from beanie import Document, PydanticObjectId
from pydantic import BaseModel, ConfigDict, Field


class LineChange(BaseModel):
    """One tailored line of the .tex, kept with what it replaced so the diff
    screen and the source screen can never disagree."""

    line_no: int = Field(ge=1)
    text: str
    previous: str | None = None


class TailoredOutput(BaseModel):
    """What the tailoring agent produced for one job."""

    job_id: PydanticObjectId
    file_path: str
    template_path: str = "templates/base_resume.tex"
    incorporated: list[str] = Field(default_factory=list)
    declined: list[str] = Field(default_factory=list)
    changes: list[LineChange] = Field(default_factory=list)


class TailoredResume(Document, TailoredOutput):
    """FR-4.4 — a .tex path and the selection set that produced it. No PDF in v1."""

    match_id: PydanticObjectId
    version: int = Field(default=1, ge=1)

    # The audit trail NFR-8 requires: every changed line traces back to these.
    selected_keys: list[str] = Field(default_factory=list)

    rendered_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "resumes"
        indexes = [
            pymongo.IndexModel(
                [("job_id", pymongo.ASCENDING), ("version", pymongo.DESCENDING)], unique=True
            ),
        ]


class ResumeStore(TailoredOutput):
    """What the tailoring agent posts once it has written the file."""


class ResumeRead(TailoredOutput):
    # Responses always carry every field; inheriting a default must not
    # make it optional in the schema.
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    id: PydanticObjectId
    match_id: PydanticObjectId
    version: int
    selected_keys: list[str]
    rendered_at: datetime
