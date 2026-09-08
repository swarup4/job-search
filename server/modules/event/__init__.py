"""Public interface of the event module."""

from modules.event.models import Event
from modules.event.router import router

NAME = "event"

__all__ = ["NAME", "Event", "router"]
