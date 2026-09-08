from datetime import UTC, datetime

from beanie import PydanticObjectId

from errors import Invalid, NotFound
from modules.job import JobStatus, JobUpdate, get_job, update_job
from modules.match.models import (
    KeywordReview,
    KeywordSelection,
    Match,
    MatchWrite,
    PendingCounts,
    ReviewState,
)


class MatchNotFound(NotFound):
    def __init__(self, job_id: PydanticObjectId) -> None:
        super().__init__(f"no match for job {job_id}")


class UnknownKeyword(Invalid):
    def __init__(self, keys: list[str]) -> None:
        super().__init__(f"not in this match's missing list: {', '.join(sorted(keys))}")


async def write_match(payload: MatchWrite) -> Match:
    await get_job(payload.job_id)  # raises JobNotFound; matches never dangle

    match = await Match.find_one(Match.job_id == payload.job_id)
    if match is None:
        match = Match(**payload.model_dump())
    else:
        # A re-score replaces the agent's findings and resets the gate: the user
        # must not inherit an approval given against different keywords.
        for field, value in payload.model_dump(exclude={"job_id"}).items():
            setattr(match, field, value)
        match.review = KeywordReview()
        match.scored_at = datetime.now(UTC)

    await match.save()
    await update_job(payload.job_id, JobUpdate(status=JobStatus.REVIEWED))
    return match


async def get_match(job_id: PydanticObjectId) -> Match:
    match = await Match.find_one(Match.job_id == job_id)
    if match is None:
        raise MatchNotFound(job_id)
    return match


async def record_selection(job_id: PydanticObjectId, payload: KeywordSelection) -> Match:
    """The keyword interrupt resolving. Only keys the agent offered may be selected."""
    match = await get_match(job_id)

    offered = {keyword.key for keyword in match.missing}
    unknown = [key for key in payload.selected_keys if key not in offered]
    if unknown:
        raise UnknownKeyword(unknown)

    match.review = KeywordReview(
        state=ReviewState.SKIPPED if payload.skip else ReviewState.SELECTED,
        selected_keys=[] if payload.skip else list(dict.fromkeys(payload.selected_keys)),
        reviewed_at=datetime.now(UTC),
    )
    await match.save()
    return match


async def pending_counts() -> PendingCounts:
    return PendingCounts(
        keyword_selections=await Match.find(Match.review.state == ReviewState.PENDING).count()
    )
