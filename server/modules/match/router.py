from __future__ import annotations

from beanie import PydanticObjectId
from fastapi import APIRouter, HTTPException, status

from modules.match import service
from modules.match.models import (
    KeywordSelection,
    MatchRead,
    MatchWrite,
    PendingCounts,
)

router = APIRouter(tags=["match"])


@router.post("", response_model=MatchRead, status_code=status.HTTP_201_CREATED)
async def write_match(payload: MatchWrite) -> MatchRead:
    try:
        return MatchRead.of(await service.write_match(payload))
    except service.JobNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/pending", response_model=PendingCounts)
async def pending() -> PendingCounts:
    return await service.pending_counts()


@router.get("/{job_id}", response_model=MatchRead)
async def get_match(job_id: PydanticObjectId) -> MatchRead:
    try:
        return MatchRead.of(await service.get_match(job_id))
    except service.MatchNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/{job_id}/selection", response_model=MatchRead)
async def record_selection(job_id: PydanticObjectId, payload: KeywordSelection) -> MatchRead:
    """Resolves the FR-7.3 keyword interrupt. There is no bulk variant on purpose."""
    try:
        return MatchRead.of(await service.record_selection(job_id, payload))
    except service.MatchNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except service.UnknownKeyword as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
