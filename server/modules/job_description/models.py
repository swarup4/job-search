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


class DescriptionStatus(StrEnum):
    """Captured, turned into a posting, or found not to be one."""

    RAW = "raw"
    PARSED = "parsed"
    DISCARDED = "discarded"


class JobDescriptionCreate(BaseModel):
    """One career page, converted to markdown in the browser. Nothing here is parsed
    into job fields — that happens later, off the stored text."""

    # `markdown` is the wire name the extension has always sent; the stored field is
    # `jdText` to match the rest of the codebase.
    model_config = ConfigDict(populate_by_name=True)

    # A plain string, not HttpUrl: a capture is worth keeping even from an odd but
    # real URL, and a stricter type would trade the evidence for a 422.
    url: str
    pageTitle: str = ""
    # Empty markdown is the shadow-DOM failure mode and belongs in the 422 rather
    # than in the collection.
    jdText: str = Field(min_length=1, max_length=MAX_MARKDOWN_CHARS, alias="markdown")
    # Rendered from the markdown for the job detail page. Never embedded — tags in
    # the vector would cost similarity accuracy for nothing.
    htmlString: str = ""
    region: CaptureRegion
    textLength: int
    # Also inline in the markdown. Flat and deduped here because the apply URL is
    # the one link that later becomes `Application.applyUrl`, and hunting it out
    # of prose is not the job of whatever reads this next.
    links: list[str] = Field(default_factory=list, max_length=MAX_LINKS)
    contentHash: str | None = None


class JobDescription(Document):
    # Null until the capture is parsed into a posting. The extension captures a page
    # before any job exists, so this cannot be required — but a job may own at most
    # one description, which the partial unique index below enforces.
    jobId: PydanticObjectId | None = None

    url: str
    pageTitle: str
    region: CaptureRegion

    jdText: str
    htmlString: str = ""
    links: list[str] = Field(default_factory=list)

    # The tech stack the posting asks for, normalised to single tokens. Parsed out
    # of `jdText`, so it belongs with the prose rather than with the listing.
    requirements: list[str] = Field(default_factory=list)

    # Built from `jdText`, never from `htmlString`. Null until the AI tier has
    # embedded it; a `$vectorSearch` index covers this field.
    embedding: list[float] | None = None

    # Both stored rather than derived, so a listing can answer "did this work?"
    # without loading the text. Visible text near zero is a sign-in wall or a
    # shell that never rendered — the one tell those failures share.
    markdownLength: int
    textLength: int

    contentHash: str

    status: DescriptionStatus = DescriptionStatus.RAW
    capturedAt: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "job_descriptions"
        indexes = [
            pymongo.IndexModel([("contentHash", pymongo.ASCENDING)], unique=True),
            # One description per job, but only among rows that have been linked —
            # a plain unique index would collide every unparsed capture on null.
            pymongo.IndexModel(
                [("jobId", pymongo.ASCENDING)],
                unique=True,
                partialFilterExpression={"jobId": {"$type": "objectId"}},
            ),
            pymongo.IndexModel([("status", pymongo.ASCENDING), ("capturedAt", pymongo.DESCENDING)]),
            pymongo.IndexModel([("url", pymongo.ASCENDING)]),
        ]


class JobDescriptionRead(BaseModel):
    """`jdText`, `htmlString`, `links` and `embedding` stay out — a page of
    descriptions is a list, not a read. `GET /job-description/{id}` returns the text."""

    # A response always carries every field, defaults included.
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    id: PydanticObjectId
    jobId: PydanticObjectId | None = None
    url: str
    pageTitle: str
    region: CaptureRegion
    markdownLength: int
    textLength: int
    status: DescriptionStatus
    capturedAt: datetime


class JobDescriptionDetail(JobDescriptionRead):
    """The one response that carries the text, asked for by id. `embedding` is still
    withheld: it is several kilobytes of floats no caller of this endpoint reads."""

    jdText: str
    htmlString: str = ""
    links: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)


class JobDescriptionUpdate(BaseModel):
    """What parsing learns after the capture was stored. Every field optional: a
    PATCH sends only what changed."""

    requirements: list[str] | None = None
    htmlString: str | None = None


class JobDescriptionCreated(BaseModel):
    """`duplicate` is how the popup says "already captured" instead of saving twice."""

    id: PydanticObjectId
    duplicate: bool


class EmbeddingWrite(BaseModel):
    """What the AI tier posts once it has a vector. Kept apart from the capture body
    because nothing that captures a page is in a position to embed it."""

    embedding: list[float] = Field(min_length=1)
