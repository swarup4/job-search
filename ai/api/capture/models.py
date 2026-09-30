from __future__ import annotations

from pydantic import BaseModel


class CaptureResult(BaseModel):
    """What the popup shows: the job made from the page, or why there is none."""

    parsed: bool
    jobId: str | None = None
    duplicate: bool = False
    title: str | None = None
    company: str | None = None
    technologies: int = 0
    reason: str | None = None
