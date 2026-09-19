from datetime import UTC, datetime
from enum import StrEnum

import pymongo
from beanie import Document, PydanticObjectId
from pydantic import BaseModel, ConfigDict, Field

# A posting as markdown is a few kilobytes. This is a backstop against something
# that is not a posting, not a limit any real capture should approach.
MAX_MARKDOWN_CHARS = 400_000

# Enough to hold a posting's apply link and its neighbours without storing a
# sitemap when the region heuristic picks up a nav.
MAX_LINKS = 200


class CaptureRegion(StrEnum):
    """Which rule picked the stored fragment. `body` means none of them were
    confident, so the whole page is in there and a parser should expect noise."""

    MAIN = "main"
    ARTICLE = "article"
    HEURISTIC = "heuristic"
    BODY = "body"


class CaptureStatus(StrEnum):
    """Captured, turned into a posting, or found not to be one."""

    RAW = "raw"
    PARSED = "parsed"
    DISCARDED = "discarded"


class CaptureCreate(BaseModel):
    """One career page, converted to markdown in the browser. Nothing here is
    parsed into job fields — that happens later, off the stored text."""

    # A plain string, not HttpUrl: a capture is worth keeping even from an odd but
    # real URL, and a stricter type would trade the evidence for a 422.
    url: str
    pageTitle: str = ""
    # Empty markdown is the shadow-DOM failure mode and belongs in the 422 rather
    # than in the collection.
    markdown: str = Field(min_length=1, max_length=MAX_MARKDOWN_CHARS)
    region: CaptureRegion
    textLength: int
    # Also inline in the markdown. Flat and deduped here because the apply URL is
    # the one link that later becomes `Application.applyUrl`, and hunting it out
    # of prose is not the job of whatever reads this next.
    links: list[str] = Field(default_factory=list, max_length=MAX_LINKS)
    contentHash: str | None = None


class Capture(Document):
    # The account this capture belongs to. Every query filters on it.
    userId: PydanticObjectId

    url: str
    pageTitle: str
    region: CaptureRegion

    markdown: str
    links: list[str] = Field(default_factory=list)

    # Both stored rather than derived, so a listing can answer "did this work?"
    # without loading the text. Visible text near zero is a sign-in wall or a
    # shell that never rendered — the one tell those failures share.
    markdownLength: int
    textLength: int

    contentHash: str

    status: CaptureStatus = CaptureStatus.RAW
    # Set when a capture becomes a posting. Nothing writes it yet.
    jobId: PydanticObjectId | None = None
    capturedAt: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "captures"
        indexes = [
            # Unique per user, as jobs are: the same page captured by two people is
            # two rows, and one user's capture must not dedup another's away.
            pymongo.IndexModel(
                [("userId", pymongo.ASCENDING), ("contentHash", pymongo.ASCENDING)], unique=True
            ),
            pymongo.IndexModel(
                [
                    ("userId", pymongo.ASCENDING),
                    ("status", pymongo.ASCENDING),
                    ("capturedAt", pymongo.DESCENDING),
                ]
            ),
            pymongo.IndexModel([("userId", pymongo.ASCENDING), ("url", pymongo.ASCENDING)]),
        ]


class CaptureRead(BaseModel):
    """`markdown` and `links` stay out — a page of captures is a list, not a read.
    `GET /capture/{id}` is how you get the text back."""

    # A response always carries every field, defaults included.
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    id: PydanticObjectId
    url: str
    pageTitle: str
    region: CaptureRegion
    markdownLength: int
    textLength: int
    status: CaptureStatus
    jobId: PydanticObjectId | None = None
    capturedAt: datetime


class CaptureDetail(CaptureRead):
    """The one response that carries the text, asked for by id."""

    markdown: str
    links: list[str] = Field(default_factory=list)


class CaptureCreated(BaseModel):
    """`duplicate` is how the popup says "already captured" instead of saving twice."""

    id: PydanticObjectId
    duplicate: bool
