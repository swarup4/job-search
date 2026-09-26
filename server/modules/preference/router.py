from fastapi import APIRouter

from modules.account import CurrentUser
from modules.preference import service
from modules.preference.models import Preference, PreferenceFields, PreferenceRead

router = APIRouter(tags=["preference"])


@router.get("", response_model=PreferenceRead)
async def get_preference(user_id: CurrentUser) -> Preference:
    return await service.get_preference(user_id)


@router.put("", response_model=PreferenceRead)
async def save_preference(payload: PreferenceFields, user_id: CurrentUser) -> Preference:
    return await service.save_preference(user_id, payload)
