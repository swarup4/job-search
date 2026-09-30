"""Public interface of the capture module. Nothing outside imports past this file."""

from api.capture.router import router

PREFIX = "capture"

__all__ = ["PREFIX", "router"]
