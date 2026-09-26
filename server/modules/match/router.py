from beanie import PydanticObjectId
from fastapi import APIRouter, Query, status

from modules.account import CurrentUser
from modules.match import service
from modules.match.models import (
    KeywordSelection,
    Match,
    MatchRead,
    MatchSummary,
    MatchWrite,
    PendingCounts,
    UnscoredJobs,
)

router = APIRouter(tags=["match"])


@router.get("/unscored", response_model=UnscoredJobs)
async def unscored(user_id: CurrentUser, limit: int = Query(default=10, ge=0, le=50)) -> UnscoredJobs:
    return await service.unscored(user_id, limit)


@router.get("/pending", response_model=PendingCounts)
async def pending(user_id: CurrentUser) -> PendingCounts:
    return await service.pending_counts(user_id)


@router.get("/summaries", response_model=list[MatchSummary])
async def summaries(
    user_id: CurrentUser, job_ids: list[PydanticObjectId] = Query(alias="jobIds", max_length=200)
) -> list[MatchSummary]:
    return await service.summaries(user_id, job_ids)


@router.post("/selection/{job_id}", response_model=MatchRead)
async def record_selection(
    job_id: PydanticObjectId, payload: KeywordSelection, user_id: CurrentUser
) -> Match:
    """Resolves the FR-7.3 keyword interrupt. There is no bulk variant on purpose."""
    return await service.record_selection(user_id, job_id, payload)


@router.post("/writeMatch", response_model=MatchRead, status_code=status.HTTP_201_CREATED)
async def write_match(payload: MatchWrite, user_id: CurrentUser) -> Match:
    return await service.write_match(user_id, payload)


@router.get("/getMatch/{job_id}", response_model=MatchRead)
async def get_match(job_id: PydanticObjectId, user_id: CurrentUser) -> Match:
    return await service.get_match(user_id, job_id)
