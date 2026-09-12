from beanie import PydanticObjectId
from fastapi import APIRouter, status

from modules.account import CurrentUser
from modules.match import service
from modules.match.models import (
    KeywordSelection,
    Match,
    MatchRead,
    MatchWrite,
    PendingCounts,
)

router = APIRouter(tags=["match"])


@router.get("/pending", response_model=PendingCounts)
async def pending(user_id: CurrentUser) -> PendingCounts:
    return await service.pending_counts(user_id)


@router.post("/selection/{job_id}", response_model=MatchRead)
async def record_selection(
    job_id: PydanticObjectId, payload: KeywordSelection, user_id: CurrentUser
) -> Match:
    """Resolves the FR-7.3 keyword interrupt. There is no bulk variant on purpose."""
    return await service.record_selection(user_id, job_id, payload)


@router.post("", response_model=MatchRead, status_code=status.HTTP_201_CREATED)
async def write_match(payload: MatchWrite, user_id: CurrentUser) -> Match:
    return await service.write_match(user_id, payload)


@router.get("/{job_id}", response_model=MatchRead)
async def get_match(job_id: PydanticObjectId, user_id: CurrentUser) -> Match:
    return await service.get_match(user_id, job_id)
