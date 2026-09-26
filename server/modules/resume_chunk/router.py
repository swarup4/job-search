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
async def pending_chunks(user_id: CurrentUser, limit: int = 200) -> list[ResumeChunk]:
    """The AI tier's work queue — everything of mine still waiting for a vector."""
    return await service.pending_chunks(user_id, limit)


@router.put("/embeddings", response_model=EmbeddingsStored)
async def store_embeddings(payload: EmbeddingBatch, user_id: CurrentUser) -> EmbeddingsStored:
    return EmbeddingsStored(stored=await service.store_embeddings(user_id, payload))


@router.post("/search", response_model=list[ChunkMatch])
async def search(payload: SearchQuery, user_id: CurrentUser) -> list[ChunkMatch]:
    """Nearest chunks to an already-embedded query. Atlas only — see `service.search`."""
    return await service.search(user_id, payload.vector, payload.limit)


@router.get("", response_model=list[ResumeChunkRead])
async def list_chunks(user_id: CurrentUser, limit: int = 200, skip: int = 0) -> list[ResumeChunk]:
    return await service.list_chunks(user_id, limit, skip)
