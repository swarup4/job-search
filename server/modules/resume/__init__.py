"""Public interface of the resume module."""

from modules.resume.models import TailoredResume
from modules.resume.router import router

NAME = "resume"

__all__ = ["NAME", "TailoredResume", "router"]
