from datetime import UTC, datetime
from enum import StrEnum

import pymongo
from beanie import Document, PydanticObjectId
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, computed_field


class ApplicationStatus(StrEnum):
    """STAGED is pre-submit. Everything after it is a human's doing."""

    STAGED = "staged"
    APPLIED = "applied"
    VIEWED = "viewed"
    INTERVIEW = "interview"
    OFFER = "offer"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class AtsPlatform(StrEnum):
    WORKDAY = "workday"
    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    LINKEDIN_EASY_APPLY = "linkedin_easy_apply"
    OTHER = "other"


class FieldFill(BaseModel):
    """What the extension put in one field. FR-5.4 — an unmarked fill is a silent edit."""

    selector: str
    label: str
    value: str
    source: str  # "profile" | "answer_bank" | "llm_fallback"
    highlighted: bool = True


class ScreeningAnswer(BaseModel):
    question: str
    answer: str | None = None
    answeredByUser: bool = False


class ApplicationStage(BaseModel):
    """What `resume` posts once a .tex exists for the job."""

    jobId: PydanticObjectId
    resumeId: PydanticObjectId
    texPath: str
    ats: AtsPlatform = AtsPlatform.OTHER
    applyUrl: HttpUrl | None = None


class Application(Document):
    userId: PydanticObjectId
    jobId: PydanticObjectId
    resumeId: PydanticObjectId
    texPath: str
    ats: AtsPlatform = AtsPlatform.OTHER
    applyUrl: HttpUrl | None = None

    status: ApplicationStatus = ApplicationStatus.STAGED
    fieldsFilled: list[FieldFill] = Field(default_factory=list)
    screeningAnswers: list[ScreeningAnswer] = Field(default_factory=list)

    # FR-5.3 / NFR-7. Nothing in this codebase ever sets this; only a human's
    # confirmation through the dashboard or the extension popup does.
    approvedByUser: bool = False

    stagedAt: datetime = Field(default_factory=lambda: datetime.now(UTC))
    submittedAt: datetime | None = None
    lastActivityAt: datetime | None = None
    lastActivityNote: str | None = None
    followUpDueAt: datetime | None = None
    followUpSentAt: datetime | None = None

    class Settings:
        name = "applications"
        indexes = [
            pymongo.IndexModel([("userId", pymongo.ASCENDING), ("jobId", pymongo.ASCENDING)]),
            pymongo.IndexModel(
                [
                    ("userId", pymongo.ASCENDING),
                    ("status", pymongo.ASCENDING),
                    ("stagedAt", pymongo.DESCENDING),
                ]
            ),
            pymongo.IndexModel(
                [("userId", pymongo.ASCENDING), ("followUpDueAt", pymongo.ASCENDING)]
            ),
        ]


class AnswerBank(Document):
    """Reusable screening answers (FR-5.2). One document per question key."""

    userId: PydanticObjectId
    key: str
    question: str
    answer: str
    tags: list[str] = Field(default_factory=list)
    usedCount: int = 0
    createdAt: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "answer_bank"
        # Unique per user: two people both have an answer keyed "notice_period".
        indexes = [
            pymongo.IndexModel(
                [("userId", pymongo.ASCENDING), ("key", pymongo.ASCENDING)], unique=True
            )
        ]


class ApplicationFill(BaseModel):
    """The extension reporting what it filled. Reporting only — it submits nothing."""

    fieldsFilled: list[FieldFill] = Field(default_factory=list)
    screeningAnswers: list[ScreeningAnswer] = Field(default_factory=list)


class StatusTransition(BaseModel):
    status: ApplicationStatus
    note: str | None = None
    # Moving to APPLIED is the user confirming they pressed Submit themselves.
    confirmedByUser: bool = False


class ApplicationRead(BaseModel):
    # A response always carries every field, defaults included.
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    id: PydanticObjectId
    jobId: PydanticObjectId
    resumeId: PydanticObjectId
    texPath: str
    ats: AtsPlatform = AtsPlatform.OTHER
    applyUrl: HttpUrl | None = None
    status: ApplicationStatus = ApplicationStatus.STAGED
    fieldsFilled: list[FieldFill] = Field(default_factory=list)
    screeningAnswers: list[ScreeningAnswer] = Field(default_factory=list)
    approvedByUser: bool = False
    stagedAt: datetime = Field(default_factory=lambda: datetime.now(UTC))
    submittedAt: datetime | None = None
    lastActivityAt: datetime | None = None
    lastActivityNote: str | None = None
    followUpDueAt: datetime | None = None
    followUpSentAt: datetime | None = None

    @computed_field
    @property
    def needs_answer(self) -> int:
        return sum(1 for answer in self.screeningAnswers if not answer.answer)
