"""Public interface of the preference module — what discovery looks for, per user.
Nothing outside imports past this file."""

from modules.preference.models import Preference
from modules.preference.router import router

NAME = "preference"

__all__ = ["NAME", "Preference", "router"]
