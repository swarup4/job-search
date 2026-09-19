from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

import pymongo
from beanie import Document, PydanticObjectId
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ReviewState(StrEnum):
    """FR-7.3 — the keyword gate. A match leaves PENDING only by user action."""

    PENDING = "pending"
    SELECTED = "selected"
    SKIPPED = "skipped"


class PresentKeyword(BaseModel):
    """Already in the resume. Read-only on the selection screen."""

    label: str
    chunkId: str | None = None


class MissingKeyword(BaseModel):
    key: str
    label: str
    mentions: int = 1
    evidence: str
    # A profile span the agent read as this requirement in other words. Advisory: the
    # keyword stays missing and stays selectable, so FR-2.5 is untouched.
    nearMiss: str | None = None


class RiskFlag(BaseModel):
    """FR-2.4 — surfaced, never selectable. Acting on one would be a misrepresentation."""

    key: str
    title: str
    detail: str


class KeywordReview(BaseModel):
    state: ReviewState = ReviewState.PENDING
    selectedKeys: list[str] = Field(default_factory=list)
    reviewedAt: datetime | None = None

    @model_validator(mode="after")
    def _selection_requires_review(self) -> KeywordReview:
        # FR-2.5 / NFR-8: a selection that nobody made is a fabrication.
        if self.selectedKeys and self.state is ReviewState.PENDING:
            raise ValueError("selectedKeys may only be set once a user has reviewed the match")
        return self


class MatchWrite(BaseModel):
    """What the matching agent posts. The JD vector goes to Atlas, never here."""

    jobId: PydanticObjectId
    score: int = Field(ge=0, le=100)
    present: list[PresentKeyword] = Field(default_factory=list)
    missing: list[MissingKeyword] = Field(default_factory=list)
    risks: list[RiskFlag] = Field(default_factory=list)
    # Which local model produced this, so a re-score is comparable.
    modelName: str | None = None


class Match(Document):
    userId: PydanticObjectId
    jobId: PydanticObjectId
    score: int = Field(ge=0, le=100)
    present: list[PresentKeyword] = Field(default_factory=list)
    missing: list[MissingKeyword] = Field(default_factory=list)
    risks: list[RiskFlag] = Field(default_factory=list)
    modelName: str | None = None
    review: KeywordReview = Field(default_factory=KeywordReview)
    scoredAt: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "matches"
        indexes = [
            pymongo.IndexModel([("jobId", pymongo.ASCENDING)], unique=True),
            pymongo.IndexModel(
                [("userId", pymongo.ASCENDING), ("review.state", pymongo.ASCENDING)]
            ),
            pymongo.IndexModel([("userId", pymongo.ASCENDING), ("score", pymongo.DESCENDING)]),
        ]


class MatchRead(BaseModel):
    # A response always carries every field, defaults included.
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    id: PydanticObjectId
    jobId: PydanticObjectId
    score: int = Field(ge=0, le=100)
    present: list[PresentKeyword] = Field(default_factory=list)
    missing: list[MissingKeyword] = Field(default_factory=list)
    risks: list[RiskFlag] = Field(default_factory=list)
    modelName: str | None = None
    review: KeywordReview
    scoredAt: datetime


class KeywordSelection(BaseModel):
    """The user's answer at the interrupt. An empty list is a valid answer."""

    selectedKeys: list[str] = Field(default_factory=list)
    skip: bool = False


class PendingCounts(BaseModel):
    """Feeds the board's "⚠ Pending your review" banner."""

    keywordSelections: int
