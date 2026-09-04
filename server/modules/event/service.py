from beanie import PydanticObjectId

from modules.event.models import Event, EventAppend, EventType


async def append_event(payload: EventAppend) -> Event:
    event = Event(**payload.model_dump())
    await event.insert()
    return event


async def list_events(
    job_id: PydanticObjectId | None = None,
    event_type: EventType | None = None,
    limit: int = 100,
) -> list[Event]:
    query: dict[str, object] = {}
    if job_id is not None:
        query["job_id"] = job_id
    if event_type is not None:
        query["event_type"] = event_type
    return await Event.find(query).sort(-Event.occurred_at).limit(limit).to_list()
