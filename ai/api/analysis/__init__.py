"""Public interface of the analysis module. Nothing outside imports past this file."""

from api.analysis.router import router

PREFIX = "runs/analysis"

__all__ = ["PREFIX", "router"]
