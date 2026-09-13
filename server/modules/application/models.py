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
    answered_by_user: bool = False


class ApplicationStage(BaseModel):
    """What `resume` posts once a .tex exists for the job."""

    job_id: PydanticObjectId
    resume_id: PydanticObjectId
    tex_path: str
    ats: AtsPlatform = AtsPlatform.OTHER
    apply_url: HttpUrl | None = None


class Application(Document):
    userId: PydanticObjectId
    job_id: PydanticObjectId
    resume_id: PydanticObjectId
    tex_path: str
    ats: AtsPlatform = AtsPlatform.OTHER
    apply_url: HttpUrl | None = None

    status: ApplicationStatus = ApplicationStatus.STAGED
    fields_filled: list[FieldFill] = Field(default_factory=list)
    screening_answers: list[ScreeningAnswer] = Field(default_factory=list)

    # FR-5.3 / NFR-7. Nothing in this codebase ever sets this; only a human's
    # confirmation through the dashboard or the extension popup does.
    approved_by_user: bool = False

    staged_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    submitted_at: datetime | None = None
    last_activity_at: datetime | None = None
    last_activity_note: str | None = None
    follow_up_due_at: datetime | None = None
    follow_up_sent_at: datetime | None = None

    class Settings:
        name = "applications"
        indexes = [
            pymongo.IndexModel([("userId", pymongo.ASCENDING), ("job_id", pymongo.ASCENDING)]),
            pymongo.IndexModel(
                [
                    ("userId", pymongo.ASCENDING),
                    ("status", pymongo.ASCENDING),
                    ("staged_at", pymongo.DESCENDING),
                ]
            ),
            pymongo.IndexModel(
                [("userId", pymongo.ASCENDING), ("follow_up_due_at", pymongo.ASCENDING)]
            ),
        ]


class AnswerBank(Document):
    """Reusable screening answers (FR-5.2). One document per question key."""

    userId: PydanticObjectId
    key: str
    question: str
    answer: str
    tags: list[str] = Field(default_factory=list)
    used_count: int = 0
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

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

    fields_filled: list[FieldFill] = Field(default_factory=list)
    screening_answers: list[ScreeningAnswer] = Field(default_factory=list)


class StatusTransition(BaseModel):
    status: ApplicationStatus
    note: str | None = None
    # Moving to APPLIED is the user confirming they pressed Submit themselves.
    confirmed_by_user: bool = False


class ApplicationRead(BaseModel):
    # A response always carries every field, defaults included.
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    id: PydanticObjectId
    job_id: PydanticObjectId
    resume_id: PydanticObjectId
    tex_path: str
    ats: AtsPlatform = AtsPlatform.OTHER
    apply_url: HttpUrl | None = None
    status: ApplicationStatus = ApplicationStatus.STAGED
    fields_filled: list[FieldFill] = Field(default_factory=list)
    screening_answers: list[ScreeningAnswer] = Field(default_factory=list)
    approved_by_user: bool = False
    staged_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    submitted_at: datetime | None = None
    last_activity_at: datetime | None = None
    last_activity_note: str | None = None
    follow_up_due_at: datetime | None = None
    follow_up_sent_at: datetime | None = None

    @computed_field
    @property
    def needs_answer(self) -> int:
        return sum(1 for answer in self.screening_answers if not answer.answer)
