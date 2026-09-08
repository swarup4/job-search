"""Public interface of the user module."""

from modules.user.models import User
from modules.user.router import router

NAME = "user"

__all__ = ["NAME", "User", "router"]
