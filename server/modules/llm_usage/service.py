from datetime import UTC, datetime, timedelta

from beanie import PydanticObjectId

from modules.llm_usage.models import LlmUsage, StepUsage, UsageBatch, UsageSummary


async def record(user_id: PydanticObjectId, batch: UsageBatch) -> int:
    """Append one run's calls. Nothing is merged or replaced: a usage log that could
    be rewritten would not be evidence of what a prompt change cost."""
    rows = [
        LlmUsage(**call.model_dump(), userId=user_id, runKind=batch.runKind, runId=batch.runId)
        for call in batch.calls
    ]
    await LlmUsage.insert_many(rows)
    return len(rows)


async def summary(
    user_id: PydanticObjectId, days: int = 7, run_id: str | None = None
) -> UsageSummary:
    """Totals per step, model and prompt version. One run when `run_id` is given,
    otherwise everything in the last `days` days."""
    query: dict[str, object] = {"userId": user_id}
    since: datetime | None = None
    if run_id is not None:
        query["runId"] = run_id
    else:
        since = datetime.now(UTC) - timedelta(days=days)
        query["at"] = {"$gte": since}

    rows = await LlmUsage.aggregate(
        [
            {"$match": query},
            {
                "$group": {
                    "_id": {"step": "$step", "model": "$model", "version": "$promptVersion"},
                    "calls": {"$sum": 1},
                    "retries": {"$sum": {"$cond": [{"$gt": ["$attempt", 1]}, 1, 0]}},
                    "promptTokens": {"$sum": "$promptTokens"},
                    "cachedTokens": {"$sum": "$cachedTokens"},
                    "completionTokens": {"$sum": "$completionTokens"},
                    "elapsedMs": {"$avg": "$elapsedMs"},
                }
            },
            {"$sort": {"promptTokens": -1}},
        ]
    ).to_list()

    steps = [
        StepUsage(
            step=row["_id"]["step"],
            model=row["_id"]["model"],
            promptVersion=row["_id"].get("version"),
            calls=row["calls"],
            retries=row["retries"],
            promptTokens=row["promptTokens"],
            cachedTokens=row["cachedTokens"],
            completionTokens=row["completionTokens"],
            averageElapsedMs=round(row["elapsedMs"] or 0),
        )
        for row in rows
    ]
    return UsageSummary(
        since=since,
        runId=run_id,
        calls=sum(step.calls for step in steps),
        promptTokens=sum(step.promptTokens for step in steps),
        cachedTokens=sum(step.cachedTokens for step in steps),
        completionTokens=sum(step.completionTokens for step in steps),
        steps=steps,
    )
