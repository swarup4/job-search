from fastapi import APIRouter

from modules.account import CurrentUser
from modules.skill_inventory import service
from modules.skill_inventory.models import (
    SkillInventory,
    SkillInventoryRead,
    SkillInventoryWrite,
)

# Scoped to the caller by the token, like the profile it is read from.
router = APIRouter(tags=["skill-inventory"])


@router.get("/getInventory", response_model=SkillInventoryRead)
async def get_inventory(user_id: CurrentUser) -> SkillInventory:
    """404 until the first scoring run has built one — the AI tier's cue to build it."""
    return await service.get_inventory(user_id)


@router.put("/replaceInventory", response_model=SkillInventoryRead)
async def replace_inventory(payload: SkillInventoryWrite, user_id: CurrentUser) -> SkillInventory:
    return await service.replace_inventory(user_id, payload)
