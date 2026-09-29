from datetime import UTC, datetime
from typing import Literal

import pymongo
from beanie import Document, PydanticObjectId
from pydantic import BaseModel, ConfigDict, Field, field_validator

WorkMode = Literal["on_site", "hybrid", "remote"]

# What discovery looks for before anything is saved. The same defaults as the AI
# tier's SCRAPE_* fallbacks, so an unsaved account scrapes exactly what it is shown.
DEFAULT_ROLES = ["AI", "GenAI", "Generative", "LLM", "Agentic", "Machine Learning", "ML"]
DEFAULT_LOCATIONS = ["India"]

MAX_TERMS = 30
MAX_TERM_CHARS = 60


def _clean(terms: list[str]) -> list[str]:
    """Trimmed, blanks dropped, and repeats removed ignoring case — "LLM" and "llm"
    match the same titles, so keeping both would only make the run search twice."""
    kept: list[str] = []
    seen: set[str] = set()
    for term in terms:
        term = term.strip()
        if term and term.lower() not in seen:
            seen.add(term.lower())
            kept.append(term)
    return kept


class PreferenceFields(BaseModel):
    """The whole Search targets form. A full replace: an omitted field means cleared."""

    # Matched against posting titles, as whole words.
    roles: list[str] = Field(min_length=1, max_length=MAX_TERMS)
    # Matched against the posting's description, as whole words: a posting is kept when
    # its title has a role OR its description names a skill. Optional.
    skills: list[str] = Field(default_factory=list, max_length=MAX_TERMS)
    locations: list[str] = Field(min_length=1, max_length=MAX_TERMS)
    # Saved, not used to filter: Workday rarely says which mode a posting is, and
    # dropping every posting that does not would drop most of them.
    workMode: WorkMode | None = None
    minExperience: int | None = Field(default=None, ge=0, le=50)

    @field_validator("roles", "locations")
    @classmethod
    def tidy(cls, terms: list[str]) -> list[str]:
        cleaned = _clean(terms)
        if not cleaned:
            raise ValueError("needs at least one entry")
        if any(len(term) > MAX_TERM_CHARS for term in cleaned):
            raise ValueError(f"an entry is longer than {MAX_TERM_CHARS} characters")
        return cleaned

    @field_validator("skills")
    @classmethod
    def tidy_skills(cls, terms: list[str]) -> list[str]:
        cleaned = _clean(terms)
        if any(len(term) > MAX_TERM_CHARS for term in cleaned):
            raise ValueError(f"an entry is longer than {MAX_TERM_CHARS} characters")
        return cleaned


class Preference(Document):
    userId: PydanticObjectId
    roles: list[str] = Field(default_factory=lambda: list(DEFAULT_ROLES))
    skills: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=lambda: list(DEFAULT_LOCATIONS))
    workMode: WorkMode | None = None
    minExperience: int | None = None
    createdAt: datetime = Field(default_factory=lambda: datetime.now(UTC))
    # Null until the first save, which is how the screen tells defaults from choices.
    updatedAt: datetime | None = None

    class Settings:
        name = "preferences"
        indexes = [pymongo.IndexModel([("userId", pymongo.ASCENDING)], unique=True)]


class PreferenceRead(BaseModel):
    """No `id`: there is one per user and nothing addresses it by id."""

    # A response always carries every field, defaults included.
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    roles: list[str]
    skills: list[str] = Field(default_factory=list)
    locations: list[str]
    workMode: WorkMode | None = None
    minExperience: int | None = None
    updatedAt: datetime | None = None
