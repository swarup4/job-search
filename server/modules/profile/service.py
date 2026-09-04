from datetime import UTC, datetime

from errors import Conflict, NotFound
from modules.profile.models import (
    ChunkWrite,
    Profile,
    ProfileCreate,
    ProfileUpdate,
    ResumeChunkText,
)


class ProfileNotFound(NotFound):
    """No profile document yet — the user has not filled in My details."""


class ProfileExists(Conflict):
    """Single-user by design — the one profile is created once, then edited."""


class ChunkNotFound(NotFound):
    def __init__(self, chunk_id: str) -> None:
        super().__init__(f"chunk {chunk_id} not found")


async def get_profile() -> Profile:
    # Oldest first, so repeated reads agree on which document they mean. Nothing at
    # the database level caps this collection at one row — `create_profile` is what
    # keeps it to one, and it is a service rule, not an index.
    profile = await Profile.find_all().sort("+_id").first_or_none()
    if profile is None:
        raise ProfileNotFound("no profile document")
    return profile


async def create_profile(payload: ProfileCreate) -> Profile:
    try:
        await get_profile()
    except ProfileNotFound:
        profile = Profile(**payload.model_dump())
        await profile.insert()
        return profile
    raise ProfileExists("a profile already exists; PATCH it instead")


async def update_profile(payload: ProfileUpdate) -> Profile:
    profile = await get_profile()
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(profile, field, value)
    profile.updated_at = datetime.now(UTC)
    await profile.save()
    return profile


async def get_chunk(chunk_id: str) -> ResumeChunkText:
    """The RAG second hop: ai/rag fetches text here between $vectorSearch and rerank."""
    chunk = await ResumeChunkText.find_one(ResumeChunkText.chunk_id == chunk_id)
    if chunk is None:
        raise ChunkNotFound(chunk_id)
    return chunk


async def get_chunks(chunk_ids: list[str]) -> list[ResumeChunkText]:
    return await ResumeChunkText.find({"chunk_id": {"$in": chunk_ids}}).to_list()


async def replace_chunks(chunks: list[ChunkWrite]) -> int:
    """Re-indexing the resume replaces the whole set — a partial write would leave
    orphaned text whose Atlas vector points at different words."""
    await ResumeChunkText.find_all().delete()
    if chunks:
        await ResumeChunkText.insert_many(
            [ResumeChunkText(**chunk.model_dump()) for chunk in chunks]
        )

    profile = await get_profile()
    profile.chunk_count = len(chunks)
    profile.last_indexed_at = datetime.now(UTC)
    await profile.save()
    return len(chunks)
