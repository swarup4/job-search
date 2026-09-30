"""Public interface of the settings module. Nothing outside imports past this file."""

from api.settings.router import router

PREFIX = "settings"

__all__ = ["PREFIX", "router"]
