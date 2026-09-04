"""Public interface of the profile module."""

from modules.profile.models import Profile, ResumeChunkText
from modules.profile.router import router

NAME = "profile"

__all__ = ["NAME", "Profile", "ResumeChunkText", "router"]
