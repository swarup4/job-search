from datetime import UTC, datetime
from enum import StrEnum

import pymongo
from beanie import Document, PydanticObjectId
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, computed_field


class ApplicationStatus(StrEnum):
    """SHORTLISTED and STAGED are pre-submit. Everything after STAGED is a human's doing."""

    SHORTLISTED = "shortlisted"
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
    """Where one user stands with one job. `jobs` is shared, so this row — created on
    shortlist, or by tailoring a job never shortlisted — is the only per-user record."""

    userId: PydanticObjectId
    jobId: PydanticObjectId
    # Empty until a tailored resume exists.
    resumeId: PydanticObjectId | None = None
    texPath: str | None = None
    ats: AtsPlatform = AtsPlatform.OTHER
    applyUrl: HttpUrl | None = None

    status: ApplicationStatus = ApplicationStatus.SHORTLISTED
    fieldsFilled: list[FieldFill] = Field(default_factory=list)
    screeningAnswers: list[ScreeningAnswer] = Field(default_factory=list)

    # FR-5.3 / NFR-7. Nothing in this codebase ever sets this; only a human's
    # confirmation through the dashboard or the extension popup does.
    approvedByUser: bool = False

    shortlistedAt: datetime = Field(default_factory=lambda: datetime.now(UTC))
    stagedAt: datetime | None = None
    submittedAt: datetime | None = None
    lastActivityAt: datetime | None = None
    lastActivityNote: str | None = None
    followUpDueAt: datetime | None = None
    followUpSentAt: datetime | None = None

    class Settings:
        name = "applications"
        indexes = [
            pymongo.IndexModel(
                [("userId", pymongo.ASCENDING), ("jobId", pymongo.ASCENDING)], unique=True
            ),
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


# --- the applicant's standing answers ----------------------------------------


class Address(BaseModel):
    """ATS forms want the parts separately; `profile.location` is one free-text
    line, which is right for a resume header and useless for a form."""

    line1: str | None = None
    line2: str | None = None
    city: str | None = None
    state: str | None = None
    postalCode: str | None = None
    country: str | None = None


class Demographics(BaseModel):
    """US-style EEO questions. Every field is free text and every one is optional —
    "Prefer not to say" is a real answer and the default is to answer nothing."""

    gender: str | None = None
    race: str | None = None
    veteranStatus: str | None = None
    disabilityStatus: str | None = None


class ApplicantFields(BaseModel):
    """The facts every application form asks for and no resume carries, so the
    profile has nowhere to put them. Stored once, answered everywhere.

    This is not `P4-02`: those are discovery preferences (which jobs to look for).
    These are answers about you, used only when filling a form."""

    address: Address = Field(default_factory=Address)
    demographics: Demographics = Field(default_factory=Demographics)

    totalExperienceYears: float | None = Field(default=None, ge=0, le=70)
    noticePeriod: str | None = None
    earliestStartDate: str | None = None

    currentSalary: str | None = None
    expectedSalary: str | None = None

    workAuthorization: str | None = None
    requiresSponsorship: bool | None = None
    willingToRelocate: bool | None = None

    howHeard: str | None = None
    referredBy: str | None = None


class ApplicantProfile(Document):
    userId: PydanticObjectId

    address: Address = Field(default_factory=Address)
    demographics: Demographics = Field(default_factory=Demographics)

    totalExperienceYears: float | None = None
    noticePeriod: str | None = None
    earliestStartDate: str | None = None

    currentSalary: str | None = None
    expectedSalary: str | None = None

    workAuthorization: str | None = None
    requiresSponsorship: bool | None = None
    willingToRelocate: bool | None = None

    howHeard: str | None = None
    referredBy: str | None = None

    createdAt: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "applicant_profile"
        indexes = [pymongo.IndexModel([("userId", pymongo.ASCENDING)], unique=True)]


class ApplicantRead(ApplicantFields):
    """Deliberately has no `id`: there is one per user and nothing addresses it by
    id. An unsaved one reads back as this shape with every field empty."""

    model_config = ConfigDict(json_schema_serialization_defaults_required=True)


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
    resumeId: PydanticObjectId | None = None
    texPath: str | None = None
    ats: AtsPlatform = AtsPlatform.OTHER
    applyUrl: HttpUrl | None = None
    status: ApplicationStatus = ApplicationStatus.SHORTLISTED
    fieldsFilled: list[FieldFill] = Field(default_factory=list)
    screeningAnswers: list[ScreeningAnswer] = Field(default_factory=list)
    approvedByUser: bool = False
    shortlistedAt: datetime = Field(default_factory=lambda: datetime.now(UTC))
    stagedAt: datetime | None = None
    submittedAt: datetime | None = None
    lastActivityAt: datetime | None = None
    lastActivityNote: str | None = None
    followUpDueAt: datetime | None = None
    followUpSentAt: datetime | None = None

    @computed_field
    @property
    def needs_answer(self) -> int:
        return sum(1 for answer in self.screeningAnswers if not answer.answer)


class BoardCounts(BaseModel):
    """The Pipeline's column totals for one user. `new` is every job with no application
    of theirs; `applied` folds in `viewed`, which the board does not show apart."""

    new: int = 0
    shortlisted: int = 0
    staged: int = 0
    applied: int = 0
    interview: int = 0


class BoardCard(BaseModel):
    """One Pipeline card: the job, your match's headline, and — for an application
    column — what the column says about it."""

    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    id: PydanticObjectId  # the job's, since a card opens the job
    title: str
    company: str
    location: str
    source: str
    discoveredAt: datetime
    # Your match, null until you analyze the job.
    score: int | None = None
    reviewState: str | None = None
    # The first risk's title — a card has room for one.
    risk: str | None = None
    # From your application, null in New.
    texPath: str | None = None
    stagedAt: datetime | None = None
    lastActivityAt: datetime | None = None
    lastActivityNote: str | None = None


class BoardColumn(BaseModel):
    count: int
    cards: list[BoardCard]


class Board(BaseModel):
    """The Pipeline's cards, the first few of every column. Its totals and the unscored
    count come from `GET /status`, like every other number outside a page's list."""

    columns: dict[str, BoardColumn]


class Badges(BaseModel):
    """Every number the header and sidebar show, in one read. The Applications badge is
    `keywordSelections` + `staged`; `nextJobId` is the longest-waiting keyword choice,
    which the Pipeline's review banner opens."""

    keywordSelections: int
    nextJobId: PydanticObjectId | None = None
    staged: int
    shortlisted: int


class ShortlistRow(BaseModel):
    """One job on the Shortlist screen: the listing and your match counts, joined in."""

    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    id: PydanticObjectId  # the job's, since the screen links to it
    title: str
    company: str
    location: str
    source: str
    jobType: str | None = None
    workMode: str | None = None
    salaryText: str | None = None
    postedAt: datetime | None = None
    discoveredAt: datetime
    shortlistedAt: datetime | None = None
    # Null until you analyze the job; the counts are 0 then.
    score: int | None = None
    riskCount: int = 0
    presentCount: int = 0
    missingCount: int = 0


class TrackerRow(BaseModel):
    """One application on the Applications screen, with its job's listing joined in."""

    # A response always carries every field, defaults included.
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    id: PydanticObjectId
    jobId: PydanticObjectId
    title: str
    company: str
    location: str
    listingUrl: HttpUrl | None = None
    status: ApplicationStatus
    ats: AtsPlatform = AtsPlatform.OTHER
    applyUrl: HttpUrl | None = None
    texPath: str | None = None
    # How many fields the extension filled, and how many screening questions wait on you.
    fieldsFilled: int = 0
    needsAnswer: int = 0
    shortlistedAt: datetime | None = None
    stagedAt: datetime | None = None
    submittedAt: datetime | None = None
    lastActivityAt: datetime | None = None
    lastActivityNote: str | None = None
    followUpDueAt: datetime | None = None
    followUpSentAt: datetime | None = None


class Tracker(BaseModel):
    """The Applications screen, in the order an application moves: shortlisted (being
    prepared), staged (waiting on your submit), and submitted — each newest first."""

    shortlisted: list[TrackerRow]
    staged: list[TrackerRow]
    submitted: list[TrackerRow]
