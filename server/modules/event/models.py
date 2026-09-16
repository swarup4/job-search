from datetime import UTC, datetime
from enum import StrEnum

import pymongo
from beanie import Document, PydanticObjectId
from pydantic import BaseModel, ConfigDict, Field


class EventType(StrEnum):
    JOB_DISCOVERED = "job_discovered"
    JOB_SHORTLISTED = "job_shortlisted"
    MATCH_SCORED = "match_scored"
    KEYWORDS_SELECTED = "keywords_selected"
    KEYWORDS_SKIPPED = "keywords_skipped"
    RESUME_TAILORED = "resume_tailored"
    APPLICATION_STAGED = "application_staged"
    APPLICATION_FILLED = "application_filled"
    STATUS_CHANGED = "status_changed"
    FOLLOW_UP_DRAFTED = "follow_up_drafted"
    FOLLOW_UP_SENT = "follow_up_sent"
    SHEET_SYNCED = "sheet_synced"


class Actor(StrEnum):
    """Who caused it. The audit trail behind every guardrail claim."""

    USER = "user"
    AGENT = "agent"
    EXTENSION = "extension"
    SCHEDULER = "scheduler"


class EventAppend(BaseModel):
    """Append-only: there is no update or delete on an event."""

    eventType: EventType
    actor: Actor
    jobId: PydanticObjectId | None = None
    applicationId: PydanticObjectId | None = None
    notes: str | None = None
    payload: dict[str, object] = Field(default_factory=dict)


class Event(Document):
    userId: PydanticObjectId
    eventType: EventType
    actor: Actor
    jobId: PydanticObjectId | None = None
    applicationId: PydanticObjectId | None = None
    notes: str | None = None
    payload: dict[str, object] = Field(default_factory=dict)
    occurredAt: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "events"
        indexes = [
            pymongo.IndexModel(
                [
                    ("userId", pymongo.ASCENDING),
                    ("jobId", pymongo.ASCENDING),
                    ("occurredAt", pymongo.DESCENDING),
                ]
            ),
            pymongo.IndexModel([("userId", pymongo.ASCENDING), ("eventType", pymongo.ASCENDING)]),
            pymongo.IndexModel(
                [("userId", pymongo.ASCENDING), ("occurredAt", pymongo.DESCENDING)]
            ),
        ]


class EventRead(BaseModel):
    # A response always carries every field, defaults included.
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    id: PydanticObjectId
    eventType: EventType
    actor: Actor
    jobId: PydanticObjectId | None = None
    applicationId: PydanticObjectId | None = None
    notes: str | None = None
    payload: dict[str, object] = Field(default_factory=dict)
    occurredAt: datetime
