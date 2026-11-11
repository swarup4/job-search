from typing import Annotated

from fastapi import APIRouter, Query, status

from modules.account import CurrentUser
from modules.llm_usage import service
from modules.llm_usage.models import UsageBatch, UsageStored, UsageSummary

# Scoped to the caller by the token: a run is recorded against whoever started it,
# and a summary only ever covers the caller's own calls.
router = APIRouter(tags=["llm-usage"])


@router.post("", response_model=UsageStored, status_code=status.HTTP_201_CREATED)
async def record_usage(payload: UsageBatch, user_id: CurrentUser) -> UsageStored:
    """What the AI tier posts when a run ends: every model call it made."""
    return UsageStored(stored=await service.record(user_id, payload))


@router.get("/summary", response_model=UsageSummary)
async def usage_summary(
    user_id: CurrentUser,
    days: Annotated[int, Query(ge=1, le=365)] = 7,
    run_id: Annotated[str | None, Query(alias="runId", max_length=64)] = None,
) -> UsageSummary:
    return await service.summary(user_id, days, run_id)
