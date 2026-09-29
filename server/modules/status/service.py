import asyncio
from datetime import UTC, datetime

from beanie import PydanticObjectId

from modules.application import badges, board_counts
from modules.career_source import last_run_summary
from modules.job import count_jobs
from modules.match import unscored
from modules.resume import has_base_resume
from modules.resume_chunk import stats
from modules.status.models import Status, StatusBadges, StatusJobs, StatusPipeline, StatusProfile


async def get_status(user_id: PydanticObjectId) -> Status:
    """Read through each owning module's public functions, all at once."""
    waiting, counts, total, pending, discovery, index, has_resume = await asyncio.gather(
        badges(user_id),
        board_counts(user_id),
        count_jobs(),
        unscored(user_id, 0),
        last_run_summary(),
        stats(user_id),
        has_base_resume(user_id),
    )
    return Status(
        badges=StatusBadges(
            keywordSelections=waiting.keywordSelections,
            nextJobId=waiting.nextJobId,
            shortlisted=waiting.shortlisted,
            staged=waiting.staged,
            pending=waiting.keywordSelections + waiting.staged,
        ),
        pipeline=StatusPipeline(**counts.model_dump()),
        jobs=StatusJobs(total=total, unscored=pending.total, analyzed=total - pending.total),
        discovery=discovery,
        profile=StatusProfile(
            indexedChunks=index.chunks,
            pendingChunks=index.pending,
            lastIndexedAt=index.lastIndexedAt,
            hasDefaultResume=has_resume,
        ),
        serverTime=datetime.now(UTC),
    )
