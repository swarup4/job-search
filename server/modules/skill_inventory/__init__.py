"""Public interface of the skill inventory module — the profile read into skills,
each tied to the profile line that shows it."""

from modules.skill_inventory.models import SkillEntry, SkillInventory
from modules.skill_inventory.router import router
from modules.skill_inventory.service import get_inventory

NAME = "skill-inventory"

__all__ = ["NAME", "SkillEntry", "SkillInventory", "get_inventory", "router"]
