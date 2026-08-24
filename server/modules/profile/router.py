from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from modules.profile import service
from modules.profile.models import (
    ChunkWrite,
    Preferences,
    ProfileCreate,
    ProfileRead,
    ProfileUpdate,
    ResumeChunkText,
)

router = APIRouter(tags=["profile"])


@router.get("", response_model=ProfileRead)
async def get_profile() -> ProfileRead:
    try:
        return ProfileRead.of(await service.get_profile())
    except service.ProfileNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("", response_model=ProfileRead, status_code=status.HTTP_201_CREATED)
async def create_profile(payload: ProfileCreate) -> ProfileRead:
    try:
        return ProfileRead.of(await service.create_profile(payload))
    except service.ProfileExists as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.patch("", response_model=ProfileRead)
async def update_profile(payload: ProfileUpdate) -> ProfileRead:
    try:
        return ProfileRead.of(await service.update_profile(payload))
    except service.ProfileNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/preferences", response_model=Preferences)
async def get_preferences() -> Preferences:
    try:
        return (await service.get_profile()).preferences
    except service.ProfileNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.put("/preferences", response_model=Preferences)
async def set_preferences(payload: Preferences) -> Preferences:
    try:
        profile = await service.update_profile(ProfileUpdate(preferences=payload))
    except service.ProfileNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return profile.preferences


@router.get("/chunks", response_model=list[ResumeChunkText])
async def get_chunks(chunk_id: list[str] = Query(default_factory=list)) -> list[ResumeChunkText]:
    """The RAG second hop. `ai/rag/retrieval.py` calls this between the two stages."""
    return await service.get_chunks(chunk_id)


@router.put("/chunks", response_model=int)
async def replace_chunks(chunks: list[ChunkWrite]) -> int:
    try:
        return await service.replace_chunks(chunks)
    except service.ProfileNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/chunks/{chunk_id}", response_model=ResumeChunkText)
async def get_chunk(chunk_id: str) -> ResumeChunkText:
    try:
        return await service.get_chunk(chunk_id)
    except service.ChunkNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
