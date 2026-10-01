from datetime import UTC, datetime

from beanie import PydanticObjectId

from config.errors import NotFound
from modules.skill_inventory.models import SkillInventory, SkillInventoryWrite


class SkillInventoryNotFound(NotFound):
    def __init__(self) -> None:
        super().__init__("no skill inventory has been built for this profile yet")


async def get_inventory(user_id: PydanticObjectId) -> SkillInventory:
    inventory = await SkillInventory.find_one(SkillInventory.userId == user_id)
    if inventory is None:
        raise SkillInventoryNotFound()
    return inventory


async def replace_inventory(
    user_id: PydanticObjectId, payload: SkillInventoryWrite
) -> SkillInventory:
    """Whole replacement: an inventory is one reading of one profile version, and
    keeping entries from an older reading would cite lines that may be gone."""
    inventory = await SkillInventory.find_one(SkillInventory.userId == user_id)
    if inventory is None:
        inventory = SkillInventory(userId=user_id, **payload.model_dump())
        await inventory.insert()
        return inventory

    inventory.profileHash = payload.profileHash
    inventory.modelName = payload.modelName
    inventory.skills = payload.skills
    inventory.builtAt = datetime.now(UTC)
    await inventory.save()
    return inventory
