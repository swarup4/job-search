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


class ApplicationTarget(BaseModel):
    """Where this application goes and which .tex belongs to it."""

    job_id: PydanticObjectId
    resume_id: PydanticObjectId
    tex_path: str
    ats: AtsPlatform = AtsPlatform.OTHER
    apply_url: HttpUrl | None = None


class ApplicationProgress(BaseModel):
    """Everything the pipeline board reads. Only a human moves any of it forward."""

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


class Application(Document, ApplicationTarget, ApplicationProgress):
    class Settings:
        name = "applications"
        indexes = [
            pymongo.IndexModel([("job_id", pymongo.ASCENDING)]),
            pymongo.IndexModel([("status", pymongo.ASCENDING), ("staged_at", pymongo.DESCENDING)]),
            pymongo.IndexModel([("follow_up_due_at", pymongo.ASCENDING)]),
        ]


class AnswerBank(Document):
    """Reusable screening answers (FR-5.2). One document per question key."""

    key: str
    question: str
    answer: str
    tags: list[str] = Field(default_factory=list)
    used_count: int = 0
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "answer_bank"
        indexes = [pymongo.IndexModel([("key", pymongo.ASCENDING)], unique=True)]


class ApplicationStage(ApplicationTarget):
    """What `resume` posts once a .tex exists for the job."""


class ApplicationFill(BaseModel):
    """The extension reporting what it filled. Reporting only — it submits nothing."""

    fields_filled: list[FieldFill] = Field(default_factory=list)
    screening_answers: list[ScreeningAnswer] = Field(default_factory=list)


class StatusTransition(BaseModel):
    status: ApplicationStatus
    note: str | None = None
    # Moving to APPLIED is the user confirming they pressed Submit themselves.
    confirmed_by_user: bool = False


class ApplicationRead(ApplicationTarget, ApplicationProgress):
    # Responses always carry every field; inheriting a default must not
    # make it optional in the schema.
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    id: PydanticObjectId

    @computed_field
    @property
    def needs_answer(self) -> int:
        return sum(1 for answer in self.screening_answers if not answer.answer)
