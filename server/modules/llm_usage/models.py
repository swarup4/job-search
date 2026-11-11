from datetime import UTC, datetime

import pymongo
from beanie import Document, PydanticObjectId
from pydantic import BaseModel, ConfigDict, Field

# A scoring run is a few calls a job, so a run of fifty jobs fits one batch. Longer
# runs are sent in several.
MAX_CALLS_PER_BATCH = 500


class UsageCall(BaseModel):
    """One request the AI tier made to the model. The server only stores it: the
    counts are the model server's own, taken from its reply."""

    # The shape the call asked for, which names the pipeline step — "BriefDraft",
    # "Comparison", "PlacementPlan".
    step: str = Field(min_length=1, max_length=80)
    model: str = Field(min_length=1, max_length=200)
    # That step's prompt version in the AI tier. Null for a step that has none.
    promptVersion: int | None = Field(default=None, ge=1)
    # 1 for the first try; 2 and 3 are schema-repair retries of the same answer.
    attempt: int = Field(default=1, ge=1)
    promptTokens: int = Field(ge=0)
    # The part of `promptTokens` the model server answered from its cache. Zero from
    # a server that does not report it.
    cachedTokens: int = Field(default=0, ge=0)
    completionTokens: int = Field(ge=0)
    elapsedMs: int = Field(ge=0)


class UsageBatch(BaseModel):
    """Every call of one run, or of one request that is not a run."""

    # "analysis", "scoring", "tailoring", "capture".
    runKind: str = Field(min_length=1, max_length=40)
    # The AI tier's run id. Null for a single request such as tailoring.
    runId: str | None = Field(default=None, max_length=64)
    calls: list[UsageCall] = Field(min_length=1, max_length=MAX_CALLS_PER_BATCH)


class LlmUsage(Document):
    userId: PydanticObjectId
    runKind: str
    runId: str | None = None
    step: str
    model: str
    promptVersion: int | None = None
    attempt: int = 1
    promptTokens: int
    cachedTokens: int = 0
    completionTokens: int
    elapsedMs: int
    at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "llm_usage"
        indexes = [
            pymongo.IndexModel([("userId", pymongo.ASCENDING), ("at", pymongo.DESCENDING)]),
            pymongo.IndexModel([("userId", pymongo.ASCENDING), ("runId", pymongo.ASCENDING)]),
        ]


class UsageStored(BaseModel):
    stored: int


class StepUsage(BaseModel):
    """One step under one model and one prompt version — the unit a before-and-after
    comparison is made on."""

    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    step: str
    model: str
    promptVersion: int | None = None
    calls: int
    # Calls that were a second or third attempt at the same answer.
    retries: int
    promptTokens: int
    cachedTokens: int
    completionTokens: int
    averageElapsedMs: int


class UsageSummary(BaseModel):
    """The caller's own usage since `since`, or for one run."""

    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    since: datetime | None = None
    runId: str | None = None
    calls: int
    promptTokens: int
    cachedTokens: int
    completionTokens: int
    steps: list[StepUsage]
