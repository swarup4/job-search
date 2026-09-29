from datetime import datetime

from beanie import PydanticObjectId
from pydantic import BaseModel, ConfigDict

from modules.career_source import DiscoverySummary


class StatusBadges(BaseModel):
    """The header and sidebar numbers. `pending` is the Applications badge: keyword
    choices waiting plus applications staged for submit; `nextJobId` is the oldest
    choice waiting, which the Pipeline's review banner opens."""

    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    keywordSelections: int
    nextJobId: PydanticObjectId | None = None
    shortlisted: int
    staged: int
    pending: int


class StatusPipeline(BaseModel):
    """The Pipeline's column totals. `new` is every job you have no application for;
    `applied` folds in `viewed`."""

    new: int
    shortlisted: int
    staged: int
    applied: int
    interview: int


class StatusJobs(BaseModel):
    total: int
    # Jobs you have no match for — what "Analyze N new jobs" and Refresh take.
    unscored: int
    analyzed: int


class StatusProfile(BaseModel):
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    indexedChunks: int
    # Chunks stored but not yet embedded, so not yet retrievable.
    pendingChunks: int
    lastIndexedAt: datetime | None = None
    hasDefaultResume: bool


class Status(BaseModel):
    """Every number the dashboard shows outside a page's own list, in one read."""

    badges: StatusBadges
    pipeline: StatusPipeline
    jobs: StatusJobs
    discovery: DiscoverySummary
    profile: StatusProfile
    serverTime: datetime
