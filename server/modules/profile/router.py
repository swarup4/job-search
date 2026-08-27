from __future__ import annotations

from fastapi import APIRouter, Query, status

from modules.profile import service
from modules.profile.models import (
    ChunkWrite,
    Preferences,
    Profile,
    ProfileCreate,
    ProfileRead,
    ProfileUpdate,
    ResumeChunkText,
)

router = APIRouter(tags=["profile"])


@router.get("", response_model=ProfileRead)
async def get_profile() -> Profile:
    return await service.get_profile()


@router.post("", response_model=ProfileRead, status_code=status.HTTP_201_CREATED)
async def create_profile(payload: ProfileCreate) -> Profile:
    return await service.create_profile(payload)


@router.patch("", response_model=ProfileRead)
async def update_profile(payload: ProfileUpdate) -> Profile:
    return await service.update_profile(payload)


@router.get("/preferences", response_model=Preferences)
async def get_preferences() -> Preferences:
    return (await service.get_profile()).preferences


@router.put("/preferences", response_model=Preferences)
async def set_preferences(payload: Preferences) -> Preferences:
    profile = await service.update_profile(ProfileUpdate(preferences=payload))
    return profile.preferences


@router.get("/chunks", response_model=list[ResumeChunkText])
async def get_chunks(chunk_id: list[str] = Query(default_factory=list)) -> list[ResumeChunkText]:
    """The RAG second hop. `ai/rag/retrieval.py` calls this between the two stages."""
    return await service.get_chunks(chunk_id)


@router.put("/chunks", response_model=int)
async def replace_chunks(chunks: list[ChunkWrite]) -> int:
    return await service.replace_chunks(chunks)


@router.get("/chunks/{chunk_id}", response_model=ResumeChunkText)
async def get_chunk(chunk_id: str) -> ResumeChunkText:
    return await service.get_chunk(chunk_id)
