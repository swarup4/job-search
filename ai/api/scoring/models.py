from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ScoringResult(BaseModel):
    jobId: str
    title: str = ""
    score: int | None = None
    error: str | None = None


class ScoringRun(BaseModel):
    id: str
    status: Literal["running", "done", "failed"]
    scored: int = 0
    failed: int = 0
    results: list[ScoringResult] = Field(default_factory=list)
    error: str | None = None
    startedAt: datetime
    finishedAt: datetime | None = None
