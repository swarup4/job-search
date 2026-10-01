"""Public interface of the scoring module. Nothing outside imports past this file."""

from api.scoring.router import router

PREFIX = "runs/scoring"

__all__ = ["PREFIX", "router"]
