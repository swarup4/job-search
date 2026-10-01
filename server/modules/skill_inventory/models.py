from datetime import UTC, datetime
from enum import StrEnum

import pymongo
from beanie import Document, PydanticObjectId
from pydantic import BaseModel, ConfigDict, Field, model_validator


class SkillKind(StrEnum):
    TECH = "tech"
    QUALIFICATION = "qualification"
    PRACTICE = "practice"


class SkillEntry(BaseModel):
    # Short and stable within one inventory ("s12"): the comparison model cites these
    # instead of quoting the profile, and an id it invents is simply not found.
    id: str = Field(min_length=1, max_length=16)
    label: str = Field(min_length=1, max_length=80)
    aliases: list[str] = Field(default_factory=list, max_length=10)
    kind: SkillKind
    # "Senior Engineer — LTI". Where the evidence sits, for the review popup.
    source: str = Field(default="", max_length=200)
    # Copied from the profile and checked against it by the AI tier before it is sent.
    evidence: str = Field(min_length=1, max_length=1_000)


class SkillInventoryWrite(BaseModel):
    """The profile read once into a list of skills, each tied to the line that shows
    it. Built in the AI tier; this module only stores it."""

    # A digest of the profile text the inventory was read from. The AI tier compares
    # it with the profile as it is now and rebuilds on a mismatch.
    profileHash: str = Field(min_length=8, max_length=128)
    modelName: str = Field(min_length=1, max_length=200)
    skills: list[SkillEntry] = Field(default_factory=list, max_length=300)

    @model_validator(mode="after")
    def _ids_are_unique(self) -> "SkillInventoryWrite":
        ids = [entry.id for entry in self.skills]
        if len(ids) != len(set(ids)):
            raise ValueError("skill ids must be unique")
        return self


class SkillInventory(Document):
    userId: PydanticObjectId
    profileHash: str
    modelName: str
    skills: list[SkillEntry] = Field(default_factory=list)
    builtAt: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "skill_inventories"
        indexes = [pymongo.IndexModel([("userId", pymongo.ASCENDING)], unique=True)]


class SkillInventoryRead(BaseModel):
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    profileHash: str
    modelName: str
    skills: list[SkillEntry]
    builtAt: datetime
