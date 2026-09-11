from datetime import UTC, datetime
from enum import StrEnum

import pymongo
from beanie import Document, PydanticObjectId
from pydantic import BaseModel, ConfigDict, Field


class ContactStyle(StrEnum):
    CONTACTITEM = "contactitem"
    PLAIN = "plain"


class SkillsStyle(StrEnum):
    GRID = "grid"
    PILLS = "pills"


class ExperienceStyle(StrEnum):
    JOBTITLE = "jobtitle"
    TIMELINEROLE = "timelinerole"


class LocationStyle(StrEnum):
    FULL = "full"
    CITY = "city"


class TemplateStyle(BaseModel):
    """How this design lays out the blocks that differ between templates.

    All of it except `location` is read off the uploaded .tex — see
    `service.infer_style`. A `%%!` directive line in the .tex overrides any of it.
    """

    contact: ContactStyle = ContactStyle.CONTACTITEM
    skills: SkillsStyle = SkillsStyle.PILLS
    experience: ExperienceStyle = ExperienceStyle.JOBTITLE
    # Editorial, not structural: nothing in the .tex reveals it, so it defaults.
    location: LocationStyle = LocationStyle.FULL
    columns: int = Field(default=4, ge=1, le=6)


class Template(Document):
    name: str
    tex: str
    style: TemplateStyle = Field(default_factory=TemplateStyle)
    tokens: list[str] = Field(default_factory=list)
    # Previews stay on disk: a 300 KB PNG per row would be dragged through every list.
    preview_path: str | None = None
    # False archives it: kept for the resumes already built from it, hidden from the picker.
    status: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "templates"
        indexes = [
            pymongo.IndexModel([("name", pymongo.ASCENDING)], unique=True),
            pymongo.IndexModel([("status", pymongo.ASCENDING), ("name", pymongo.ASCENDING)]),
        ]


class TemplateRead(BaseModel):
    """The picker's row. `tex` is deliberately absent — a listing does not need it."""

    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    id: PydanticObjectId
    name: str
    style: TemplateStyle
    tokens: list[str]
    has_preview: bool
    status: bool
    created_at: datetime
    updated_at: datetime


class TemplateSource(TemplateRead):
    """One template with its raw, unfilled .tex."""

    tex: str


class TemplateUpdate(BaseModel):
    """Every field optional: a PATCH sends only what changed."""

    name: str | None = Field(default=None, min_length=1, max_length=60)
    status: bool | None = None
    style: TemplateStyle | None = None


class RenderedResume(BaseModel):
    """A template with the profile's data substituted in. `.tex` only, no PDF (FR-4.4)."""

    id: PydanticObjectId
    name: str
    filename: str
    tex: str
