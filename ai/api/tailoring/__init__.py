"""Public interface of the tailoring module. Nothing outside imports past this file."""

from api.tailoring.router import router

PREFIX = "tailoring"

__all__ = ["PREFIX", "router"]
