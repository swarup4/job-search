"""Public interface of the resume module."""

from modules.resume.models import (
    LineChange,
    ResumeRead,
    ResumeStore,
    TailoredOutput,
    TailoredResume,
)
from modules.resume.router import router
from modules.resume.service import (
    Fabrication,
    ResumeNotFound,
    SelectionGateNotPassed,
    get_resume,
    list_versions,
    store_resume,
)

NAME = "resume"

__all__ = [
    "NAME",
    "Fabrication",
    "LineChange",
    "ResumeNotFound",
    "ResumeRead",
    "ResumeStore",
    "SelectionGateNotPassed",
    "TailoredOutput",
    "TailoredResume",
    "get_resume",
    "list_versions",
    "router",
    "store_resume",
]
