from fastapi import APIRouter

from modules.account import CurrentUser
from modules.resume_chunk import service
from modules.resume_chunk.models import (
    ChunkMatch,
    EmbeddingBatch,
    EmbeddingsStored,
    IndexStats,
    ResumeChunk,
    ResumeChunkRead,
    SearchManyQuery,
    SearchManyResult,
    SearchQuery,
)

# Every route is scoped to the caller by the token, as in the profile module: a chunk
# id in a URL is checked against `userId` before anything is written to it.
router = APIRouter(tags=["resume-chunk"])


@router.get("/stats", response_model=IndexStats)
async def index_stats(user_id: CurrentUser) -> IndexStats:
    """What the "Indexed for retrieval" panel shows."""
    return await service.stats(user_id)


@router.get("/pending", response_model=list[ResumeChunkRead])
async def pending_chunks(
    user_id: CurrentUser, limit: int = 200, model: str | None = None
) -> list[ResumeChunk]:
    """The AI tier's work queue — everything of mine still waiting for a vector, and
    with `model`, everything embedded by a different model too."""
    return await service.pending_chunks(user_id, limit, model)


@router.put("/embeddings", response_model=EmbeddingsStored)
async def store_embeddings(payload: EmbeddingBatch, user_id: CurrentUser) -> EmbeddingsStored:
    return EmbeddingsStored(stored=await service.store_embeddings(user_id, payload))


@router.post("/search", response_model=list[ChunkMatch])
async def search(payload: SearchQuery, user_id: CurrentUser) -> list[ChunkMatch]:
    """Nearest chunks to an already-embedded query, by exact cosine."""
    return await service.search(user_id, payload.vector, payload.limit, payload.model)


@router.post("/search-many", response_model=SearchManyResult)
async def search_many(payload: SearchManyQuery, user_id: CurrentUser) -> SearchManyResult:
    """`search` for several vectors at once: one list of hits per vector."""
    return SearchManyResult(
        results=await service.search_many(user_id, payload.vectors, payload.limit, payload.model)
    )
