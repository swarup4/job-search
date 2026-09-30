"""Public interface of the discovery module. Nothing outside imports past this file."""

from api.discovery.router import router

PREFIX = "runs/discovery"

__all__ = ["PREFIX", "router"]
