import hashlib
import math
from collections.abc import Sequence
from datetime import UTC, datetime

from beanie import PydanticObjectId

from config.errors import Invalid
from modules.resume_chunk.models import (
    ChunkFields,
    ChunkMatch,
    EmbeddingBatch,
    IndexStats,
    ResumeChunk,
)


def content_hash(section: str, text: str) -> str:
    """Section and text together: the same sentence under Skills and under Summary
    are two chunks, and collapsing them would lose one on re-index."""
    return hashlib.sha256(f"{section}|{text}".encode()).hexdigest()


def cosine(left: Sequence[float], right: Sequence[float]) -> float:
    """The cosine of the angle between two vectors: 1 for the same direction, 0 for
    nothing in common. This is the scale the AI tier's near-miss threshold is measured
    on, so nothing here rescales it. A zero vector is similar to nothing."""
    norm = math.sqrt(sum(a * a for a in left)) * math.sqrt(sum(b * b for b in right))
    if not norm:
        return 0.0
    return sum(a * b for a, b in zip(left, right, strict=True)) / norm


def rank(chunks: Sequence[ResumeChunk], vector: Sequence[float], limit: int) -> list[ChunkMatch]:
    """The `limit` chunks closest to `vector`, best first. Exact: every chunk is scored.

    A chunk whose vector has a different length was embedded by a different model. Its
    cosine against this query would be meaningless, so it is left out rather than
    scored — the same answer a chunk with no vector gets. Equal scores keep profile
    order, so the same query always answers the same way."""
    scored = [
        (cosine(chunk.embedding, vector), chunk)
        for chunk in chunks
        if chunk.embedding and len(chunk.embedding) == len(vector)
    ]
    scored.sort(key=lambda pair: (-pair[0], pair[1].ordinal))
    return [
        ChunkMatch(
            id=chunk.id,
            section=chunk.section,
            text=chunk.text,
            sourceRef=chunk.sourceRef,
            score=score,
        )
        for score, chunk in scored[:limit]
    ]


async def replace_chunks(user_id: PydanticObjectId, chunks: list[ChunkFields]) -> IndexStats:
    """Rewrite one user's chunk set, carrying vectors across unchanged text.

    Re-chunking is free — it is string work — so an edit anywhere rebuilds the whole
    set rather than trying to work out which rows moved. Embedding is the part that
    costs, which is why a chunk whose text survived keeps its vector and a new or
    edited one comes back with none: it is then invisible to search until the AI tier
    embeds it, so retrieval cannot serve text the user has already changed. (P6-03)
    """
    existing = await ResumeChunk.find(ResumeChunk.userId == user_id).to_list()
    carried = {
        chunk.contentHash: (chunk.embedding, chunk.embeddedAt, chunk.embeddingModel)
        for chunk in existing
        if chunk.embedding is not None
    }

    rows: list[ResumeChunk] = []
    seen: set[str] = set()
    for ordinal, fields in enumerate(chunks):
        digest = content_hash(fields.section, fields.text)
        if digest in seen:
            continue
        seen.add(digest)
        embedding, embedded_at, embedding_model = carried.get(digest, (None, None, None))
        rows.append(
            ResumeChunk(
                userId=user_id,
                section=fields.section,
                text=fields.text,
                sourceRef=fields.sourceRef,
                sourceId=fields.sourceId,
                ordinal=ordinal,
                contentHash=digest,
                embedding=embedding,
                embeddedAt=embedded_at,
                embeddingModel=embedding_model,
            )
        )

    # Delete then insert, in that order: the unique index on (userId, contentHash)
    # would reject a re-inserted row otherwise.
    await ResumeChunk.find(ResumeChunk.userId == user_id).delete()
    if rows:
        await ResumeChunk.insert_many(rows)
    return await stats(user_id)


async def pending_chunks(
    user_id: PydanticObjectId, limit: int = 200, model: str | None = None
) -> list[ResumeChunk]:
    """The AI tier's work queue: chunks with no vector yet and, when `model` is named,
    chunks whose vector came from a different model. That second group is how a change
    of embedding model re-embeds a profile without anybody clearing it by hand."""
    waiting: dict[str, object] = {"embedding": None}
    if model:
        waiting = {"$or": [{"embedding": None}, {"embeddingModel": {"$ne": model}}]}
    return (
        await ResumeChunk.find({"userId": user_id, **waiting})
        .sort(+ResumeChunk.ordinal)
        .limit(limit)
        .to_list()
    )


async def store_embeddings(user_id: PydanticObjectId, batch: EmbeddingBatch) -> int:
    """Write vectors for chunks this user owns. A chunk id that is not theirs, or
    that a re-index deleted mid-flight, is refused rather than skipped — a vector
    landing on somebody else's text is the one failure that would never surface."""
    wanted = {item.chunkId: item.embedding for item in batch.embeddings}
    rows = await ResumeChunk.find({"_id": {"$in": list(wanted)}, "userId": user_id}).to_list()

    if len(rows) != len(wanted):
        missing = sorted(str(key) for key in wanted.keys() - {row.id for row in rows})
        raise Invalid(f"no chunk of yours with id {', '.join(missing)}")

    now = datetime.now(UTC)
    for row in rows:
        row.embedding = wanted[row.id]
        row.embeddedAt = now
        row.embeddingModel = batch.model
    await ResumeChunk.replace_many(rows)
    return len(rows)


async def _embedded(user_id: PydanticObjectId, model: str | None = None) -> list[ResumeChunk]:
    """This user's chunks that have a vector, in profile order — from `model` only,
    when one is named. The filter on `userId` is the whole of the access control here:
    nothing downstream sees another row."""
    query: dict[str, object] = {"userId": user_id, "embedding": {"$ne": None}}
    if model:
        query["embeddingModel"] = model
    return await ResumeChunk.find(query).sort(+ResumeChunk.ordinal).to_list()


async def search(
    user_id: PydanticObjectId, vector: list[float], limit: int = 50, model: str | None = None
) -> list[ChunkMatch]:
    """The nearest of this user's chunks to `vector`, by exact cosine.

    Done in this process, over an ordinary query: a profile is a few dozen chunks, so
    scoring every one is fast and exact, and it runs on any MongoDB. A vector index
    earns its keep at millions of rows, which one person's resume will never reach."""
    return rank(await _embedded(user_id, model), vector, limit)


async def search_many(
    user_id: PydanticObjectId,
    vectors: list[list[float]],
    limit: int = 1,
    model: str | None = None,
) -> list[list[ChunkMatch]]:
    """`search` for several vectors, reading the chunks once for all of them."""
    chunks = await _embedded(user_id, model)
    return [rank(chunks, vector, limit) for vector in vectors]


async def stats(user_id: PydanticObjectId) -> IndexStats:
    # Counts and one row, not the collection: every chunk carries a thousand floats
    # and this answers a panel that shows four numbers.
    chunks = await ResumeChunk.find(ResumeChunk.userId == user_id).count()
    pending = await ResumeChunk.find({"userId": user_id, "embedding": None}).count()
    newest = (
        await ResumeChunk.find({"userId": user_id, "embeddedAt": {"$ne": None}})
        .sort(-ResumeChunk.embeddedAt)
        .first_or_none()
    )
    return IndexStats(
        chunks=chunks,
        embedded=chunks - pending,
        pending=pending,
        lastIndexedAt=newest.embeddedAt if newest else None,
    )
