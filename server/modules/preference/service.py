from datetime import UTC, datetime

from beanie import PydanticObjectId

from modules.preference.models import Preference, PreferenceFields


async def get_preference(user_id: PydanticObjectId) -> Preference:
    """Unsaved reads back as the defaults rather than 404: discovery needs something
    to search for on the very first run, and the screen shows what that is."""
    stored = await Preference.find_one(Preference.userId == user_id)
    return stored or Preference(userId=user_id)


async def save_preference(user_id: PydanticObjectId, payload: PreferenceFields) -> Preference:
    """Upsert, and a full replace: the Search targets form posts the whole thing."""
    stored = await Preference.find_one(Preference.userId == user_id)
    now = datetime.now(UTC)

    if stored is None:
        stored = Preference(**payload.model_dump(), userId=user_id, updatedAt=now)
        await stored.insert()
        return stored

    for field, value in payload.model_dump().items():
        setattr(stored, field, value)
    stored.updatedAt = now
    await stored.save()
    return stored
