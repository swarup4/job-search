from beanie import PydanticObjectId
from fastapi import APIRouter, status

from modules.match import service
from modules.match.models import (
    KeywordSelection,
    Match,
    MatchRead,
    MatchWrite,
    PendingCounts,
)

router = APIRouter(tags=["match"])


@router.post("", response_model=MatchRead, status_code=status.HTTP_201_CREATED)
async def write_match(payload: MatchWrite) -> Match:
    return await service.write_match(payload)


@router.get("/pending", response_model=PendingCounts)
async def pending() -> PendingCounts:
    return await service.pending_counts()


@router.get("/{job_id}", response_model=MatchRead)
async def get_match(job_id: PydanticObjectId) -> Match:
    return await service.get_match(job_id)


@router.post("/{job_id}/selection", response_model=MatchRead)
async def record_selection(job_id: PydanticObjectId, payload: KeywordSelection) -> Match:
    """Resolves the FR-7.3 keyword interrupt. There is no bulk variant on purpose."""
    return await service.record_selection(job_id, payload)
