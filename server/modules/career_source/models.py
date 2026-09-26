from datetime import UTC, datetime
from enum import StrEnum

import pymongo
from beanie import Document, PydanticObjectId
from pydantic import BaseModel, ConfigDict, Field


class Platform(StrEnum):
    """Which adapter in `ai/sources/` reads this company. A value is added when its
    adapter lands, so nothing can be registered that no code can pull."""

    WORKDAY = "workday"


class RunResult(BaseModel):
    """What one scrape of one company did. `blocked` means robots.txt refused the
    host, which is a standing answer rather than a failure to retry."""

    fetched: int = 0
    matched: int = 0
    new: int = 0
    duplicate: int = 0
    failed: int = 0
    blocked: bool = False
    error: str | None = None


class CareerSourceCreate(BaseModel):
    name: str = Field(min_length=1)
    careersUrl: str | None = None
    platform: Platform
    # Whatever the adapter needs to address this company's board — for Workday,
    # `tenant`, `wd` and `site`. Kept as strings so every platform fits one shape.
    config: dict[str, str]
    enabled: bool = True
    notes: str | None = None


class CareerSource(Document):
    # The company name written onto every job this source produces.
    name: str
    careersUrl: str | None = None
    platform: Platform
    config: dict[str, str]
    enabled: bool = True
    notes: str | None = None
    lastRunAt: datetime | None = None
    lastResult: RunResult | None = None
    createdAt: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "career_sources"
        indexes = [
            pymongo.IndexModel([("name", pymongo.ASCENDING)], unique=True),
            pymongo.IndexModel([("enabled", pymongo.ASCENDING), ("platform", pymongo.ASCENDING)]),
        ]


class CareerSourceUpdate(BaseModel):
    """Every field optional: a PATCH sends only what changed."""

    careersUrl: str | None = None
    config: dict[str, str] | None = None
    enabled: bool | None = None
    notes: str | None = None


class CareerSourceRead(BaseModel):
    # A response always carries every field, defaults included.
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    id: PydanticObjectId
    name: str
    careersUrl: str | None = None
    platform: Platform
    config: dict[str, str]
    enabled: bool
    notes: str | None = None
    lastRunAt: datetime | None = None
    lastResult: RunResult | None = None


class CareerSourceCreated(BaseModel):
    id: PydanticObjectId
