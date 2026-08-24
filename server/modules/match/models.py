from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

import pymongo
from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field, model_validator


class ReviewState(StrEnum):
    """FR-7.3 — the keyword gate. A match leaves PENDING only by user action."""

    PENDING = "pending"
    SELECTED = "selected"
    SKIPPED = "skipped"


class PresentKeyword(BaseModel):
    """Already in the resume. Read-only on the selection screen."""

    label: str
    chunk_id: str | None = None


class MissingKeyword(BaseModel):
    key: str
    label: str
    mentions: int = 1
    evidence: str


class RiskFlag(BaseModel):
    """FR-2.4 — surfaced, never selectable. Acting on one would be a misrepresentation."""

    key: str
    title: str
    detail: str


class KeywordReview(BaseModel):
    state: ReviewState = ReviewState.PENDING
    selected_keys: list[str] = Field(default_factory=list)
    reviewed_at: datetime | None = None

    @model_validator(mode="after")
    def _selection_requires_review(self) -> KeywordReview:
        # FR-2.5 / NFR-8: a selection that nobody made is a fabrication.
        if self.selected_keys and self.state is ReviewState.PENDING:
            raise ValueError("selected_keys may only be set once a user has reviewed the match")
        return self


class Match(Document):
    job_id: PydanticObjectId

    score: int = Field(ge=0, le=100)
    present: list[PresentKeyword] = Field(default_factory=list)
    missing: list[MissingKeyword] = Field(default_factory=list)
    risks: list[RiskFlag] = Field(default_factory=list)

    review: KeywordReview = Field(default_factory=KeywordReview)

    # Which local model produced this, so a re-score is comparable.
    model_name: str | None = None
    scored_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "matches"
        indexes = [
            pymongo.IndexModel([("job_id", pymongo.ASCENDING)], unique=True),
            pymongo.IndexModel([("review.state", pymongo.ASCENDING)]),
            pymongo.IndexModel([("score", pymongo.DESCENDING)]),
        ]


class MatchWrite(BaseModel):
    """What the matching agent posts. The vector goes to Atlas, never here."""

    job_id: PydanticObjectId
    score: int = Field(ge=0, le=100)
    present: list[PresentKeyword] = Field(default_factory=list)
    missing: list[MissingKeyword] = Field(default_factory=list)
    risks: list[RiskFlag] = Field(default_factory=list)
    model_name: str | None = None


class KeywordSelection(BaseModel):
    """The user's answer at the interrupt. An empty list is a valid answer."""

    selected_keys: list[str] = Field(default_factory=list)
    skip: bool = False


class MatchRead(BaseModel):
    id: PydanticObjectId
    job_id: PydanticObjectId
    score: int
    present: list[PresentKeyword]
    missing: list[MissingKeyword]
    risks: list[RiskFlag]
    review: KeywordReview
    model_name: str | None
    scored_at: datetime

    @classmethod
    def of(cls, match: Match) -> MatchRead:
        return cls(id=match.id, **match.model_dump(exclude={"id"}))


class PendingCounts(BaseModel):
    """Feeds the board's "⚠ Pending your review" banner."""

    keyword_selections: int
