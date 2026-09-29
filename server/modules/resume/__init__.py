"""Public interface of the resume module."""

from modules.resume.models import BaseResume, TailoredResume
from modules.resume.router import router
from modules.resume.service import has_base_resume

NAME = "resume"

__all__ = ["NAME", "BaseResume", "TailoredResume", "has_base_resume", "router"]
