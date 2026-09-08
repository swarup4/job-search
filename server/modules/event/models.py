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


class EventFacts(BaseModel):
    event_type: EventType
    actor: Actor
    job_id: PydanticObjectId | None = None
    application_id: PydanticObjectId | None = None
    notes: str | None = None
    payload: dict[str, object] = Field(default_factory=dict)


class Event(Document, EventFacts):
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "events"
        indexes = [
            pymongo.IndexModel(
                [("job_id", pymongo.ASCENDING), ("occurred_at", pymongo.DESCENDING)]
            ),
            pymongo.IndexModel([("event_type", pymongo.ASCENDING)]),
            pymongo.IndexModel([("occurred_at", pymongo.DESCENDING)]),
        ]


class EventAppend(EventFacts):
    """Append-only: there is no update or delete on an event."""


class EventRead(EventFacts):
    # Responses always carry every field; inheriting a default must not
    # make it optional in the schema.
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    id: PydanticObjectId
    occurred_at: datetime
