from fastapi import APIRouter

from modules.account import CurrentUser
from modules.status import service
from modules.status.models import Status

router = APIRouter(tags=["status"])


@router.get("", response_model=Status)
async def get_status(user_id: CurrentUser) -> Status:
    return await service.get_status(user_id)
