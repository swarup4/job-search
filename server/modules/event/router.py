from __future__ import annotations

from beanie import PydanticObjectId
from fastapi import APIRouter, Query, status

from modules.event import service
from modules.event.models import Event, EventAppend, EventRead, EventType

router = APIRouter(tags=["event"])


@router.get("", response_model=list[EventRead])
async def list_events(
    job_id: PydanticObjectId | None = None,
    event_type: EventType | None = None,
    limit: int = Query(default=100, le=500),
) -> list[Event]:
    return await service.list_events(job_id, event_type, limit)


@router.post("", response_model=EventRead, status_code=status.HTTP_201_CREATED)
async def append_event(payload: EventAppend) -> Event:
    return await service.append_event(payload)
