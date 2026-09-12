from beanie import PydanticObjectId

from modules.event.models import Event, EventAppend, EventType


async def append_event(user_id: PydanticObjectId, payload: EventAppend) -> Event:
    event = Event(**payload.model_dump(), userId=user_id)
    await event.insert()
    return event


async def list_events(
    user_id: PydanticObjectId,
    job_id: PydanticObjectId | None = None,
    event_type: EventType | None = None,
    limit: int = 100,
) -> list[Event]:
    query: dict[str, object] = {"userId": user_id}
    if job_id is not None:
        query["job_id"] = job_id
    if event_type is not None:
        query["event_type"] = event_type
    return await Event.find(query).sort(-Event.occurred_at).limit(limit).to_list()
