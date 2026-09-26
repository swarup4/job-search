from datetime import UTC, datetime
from enum import StrEnum

import pymongo
from beanie import Document, PydanticObjectId
from pydantic import BaseModel, ConfigDict, Field

# A chunk is one bullet, one skill or one credential. Anything longer than this came
# from a profile field being used as a scratchpad, and embedding it would average a
# paragraph into a vector that matches everything weakly.
MAX_CHUNK_CHARS = 2_000

# Below this a span carries no retrievable meaning — an empty bullet, a stray bracket.
MIN_CHUNK_CHARS = 3

# Named here rather than in `config.database`, which imports this module to register
# the document and would have to be imported back to read the name.
VECTOR_INDEX = "chunk_embedding_index"


class ChunkSection(StrEnum):
    """Which part of My Details a chunk was cut from. Retrieval returns it so a
    caller can say where an answer came from without a second lookup."""

    HEADLINE = "headline"
    SUMMARY = "summary"
    EXPERIENCE = "experience"
    PROJECT = "project"
    SKILL = "skill"
    EDUCATION = "education"
    CERTIFICATION = "certification"


class ChunkFields(BaseModel):
    """One retrievable unit, before it is stored. This is what the profile module
    hands over — it knows how to cut a profile up, and nothing about vectors."""

    section: ChunkSection
    # Exactly the text that gets embedded and exactly the text a match hands back.
    # Context lives in `sourceRef` rather than being glued on here: the near-miss
    # threshold in the AI tier was calibrated against raw spans, and prefixing them
    # would shift every cosine it compares.
    text: str = Field(min_length=MIN_CHUNK_CHARS, max_length=MAX_CHUNK_CHARS)
    # "Senior Engineer — LTI". For display, never embedded.
    sourceRef: str = ""
    # The profile row this came from, so a chunk can be traced back to the section
    # that produced it. Null for headline and summary, which live on the profile.
    sourceId: PydanticObjectId | None = None


class ResumeChunk(Document):
    userId: PydanticObjectId
    section: ChunkSection
    text: str
    sourceRef: str = ""
    sourceId: PydanticObjectId | None = None

    # Position in the profile, so a listing reads top to bottom the way the screen
    # does. Re-index rewrites it; nothing outside ordering depends on it.
    ordinal: int

    # `section|text`, which is what makes a re-index cheap: a chunk whose text did
    # not change keeps its vector instead of being embedded again.
    contentHash: str

    # Null until the AI tier has embedded it. A chunk with no vector is invisible to
    # `$vectorSearch`, which is what makes edited text un-retrievable rather than
    # stale — see P6-03.
    embedding: list[float] | None = None
    embeddedAt: datetime | None = None

    chunkedAt: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "resume_chunks"
        indexes = [
            # One row per distinct span per user. Chunking dedupes before it gets
            # here; this is what keeps a concurrent re-index from doubling the set.
            pymongo.IndexModel(
                [("userId", pymongo.ASCENDING), ("contentHash", pymongo.ASCENDING)], unique=True
            ),
            pymongo.IndexModel([("userId", pymongo.ASCENDING), ("ordinal", pymongo.ASCENDING)]),
            # The AI tier's work queue: everything of mine still missing a vector.
            pymongo.IndexModel([("userId", pymongo.ASCENDING), ("embedding", pymongo.ASCENDING)]),
        ]


class ResumeChunkRead(BaseModel):
    """A chunk as the dashboard and the AI tier see it. `embedding` stays out — a
    thousand floats nobody reading a list has a use for."""

    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    id: PydanticObjectId
    section: ChunkSection
    text: str
    sourceRef: str
    sourceId: PydanticObjectId | None = None
    ordinal: int
    # Null exactly while the chunk has no vector — the two are written together, and
    # a caller asking "is this retrievable yet?" reads this rather than a redundant
    # flag that could disagree with it.
    embeddedAt: datetime | None = None


class ChunkMatch(BaseModel):
    """A search hit. `score` is a true cosine, not Atlas's rescaled one — see
    `service.search`."""

    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    id: PydanticObjectId
    section: ChunkSection
    text: str
    sourceRef: str
    score: float


class SearchQuery(BaseModel):
    """A query vector, already embedded. The server does not embed anything: the
    model and its key live in the AI tier, and the two must agree on the model
    anyway or the search is meaningless."""

    vector: list[float] = Field(min_length=1)
    limit: int = Field(default=50, ge=1, le=200)


class ChunkEmbedding(BaseModel):
    chunkId: PydanticObjectId
    embedding: list[float] = Field(min_length=1)


class EmbeddingBatch(BaseModel):
    """Vectors for many chunks at once. Voyage embeds a whole profile in one call,
    so storing them one HTTP request at a time would be forty round trips for
    nothing."""

    embeddings: list[ChunkEmbedding] = Field(min_length=1, max_length=500)


class EmbeddingsStored(BaseModel):
    stored: int


class IndexStats(BaseModel):
    """What the "Indexed for retrieval" panel reads. `pending` is the honest number
    on that screen: those chunks exist but cannot be retrieved yet."""

    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    chunks: int
    embedded: int
    pending: int
    lastIndexedAt: datetime | None = None
