from beanie import PydanticObjectId
from fastapi import APIRouter, Query, status

from modules.account import CurrentUser
from modules.event import service
from modules.event.models import Event, EventAppend, EventRead, EventType

router = APIRouter(tags=["event"])


@router.get("", response_model=list[EventRead])
async def list_events(
    user_id: CurrentUser,
    job_id: PydanticObjectId | None = None,
    event_type: EventType | None = None,
    limit: int = Query(default=100, le=500),
) -> list[Event]:
    return await service.list_events(user_id, job_id, event_type, limit)


@router.post("", response_model=EventRead, status_code=status.HTTP_201_CREATED)
async def append_event(payload: EventAppend, user_id: CurrentUser) -> Event:
    return await service.append_event(user_id, payload)
