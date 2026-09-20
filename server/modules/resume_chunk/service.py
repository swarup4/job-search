import hashlib
from datetime import UTC, datetime

from beanie import PydanticObjectId

from config.errors import Invalid
from modules.resume_chunk.models import (
    VECTOR_INDEX,
    ChunkFields,
    ChunkMatch,
    EmbeddingBatch,
    IndexStats,
    ResumeChunk,
)

# `$vectorSearch` narrows an approximate search to this many candidates before it
# ranks them. Atlas asks for it to comfortably exceed `limit`; a profile is a few
# dozen chunks, so this is the whole collection either way.
CANDIDATE_MULTIPLIER = 20
MIN_CANDIDATES = 100


def content_hash(section: str, text: str) -> str:
    """Section and text together: the same sentence under Skills and under Summary
    are two chunks, and collapsing them would lose one on re-index."""
    return hashlib.sha256(f"{section}|{text}".encode()).hexdigest()


def cosine_from_score(score: float) -> float:
    """Atlas reports a cosine search as `(1 + cosine) / 2`, so a score of 0.5 means
    two vectors with nothing in common. The AI tier's near-miss threshold is a real
    cosine, calibrated against `rag/embeddings.py`, so the rescaling is undone here
    rather than left for every caller to remember."""
    return 2 * score - 1


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
        chunk.contentHash: (chunk.embedding, chunk.embeddedAt)
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
        embedding, embedded_at = carried.get(digest, (None, None))
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
            )
        )

    # Delete then insert, in that order: the unique index on (userId, contentHash)
    # would reject a re-inserted row otherwise.
    await ResumeChunk.find(ResumeChunk.userId == user_id).delete()
    if rows:
        await ResumeChunk.insert_many(rows)
    return await stats(user_id)


async def list_chunks(
    user_id: PydanticObjectId, limit: int = 200, skip: int = 0
) -> list[ResumeChunk]:
    return (
        await ResumeChunk.find(ResumeChunk.userId == user_id)
        .sort(+ResumeChunk.ordinal)
        .skip(skip)
        .limit(limit)
        .to_list()
    )


async def pending_chunks(user_id: PydanticObjectId, limit: int = 200) -> list[ResumeChunk]:
    """Chunks with no vector yet — the AI tier's work queue."""
    return (
        await ResumeChunk.find({"userId": user_id, "embedding": None})
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
    await ResumeChunk.replace_many(rows)
    return len(rows)


async def search(
    user_id: PydanticObjectId, vector: list[float], limit: int = 50
) -> list[ChunkMatch]:
    """Approximate nearest neighbours over this user's chunks.

    Atlas only — `$vectorSearch` is not a MongoDB aggregation stage, it is a Search
    one, and a local server answers with an error rather than an empty list. The
    `userId` filter is part of the index definition, not a `$match` after it: an ANN
    search filtered afterwards returns fewer rows than asked for, or none.
    """
    pipeline = [
        {
            "$vectorSearch": {
                "index": VECTOR_INDEX,
                "path": "embedding",
                "queryVector": vector,
                "numCandidates": max(MIN_CANDIDATES, limit * CANDIDATE_MULTIPLIER),
                "limit": limit,
                "filter": {"userId": user_id},
            }
        },
        {
            "$project": {
                "text": 1,
                "section": 1,
                "sourceRef": 1,
                "score": {"$meta": "vectorSearchScore"},
            }
        },
    ]

    cursor = await ResumeChunk.get_pymongo_collection().aggregate(pipeline)
    return [
        ChunkMatch(
            id=row["_id"],
            section=row["section"],
            text=row["text"],
            sourceRef=row.get("sourceRef", ""),
            score=cosine_from_score(row["score"]),
        )
        for row in await cursor.to_list(limit)
    ]


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
