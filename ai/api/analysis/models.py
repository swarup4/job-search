from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from agents.analysis import AnalysisOutcome

# A bulk click analyzes at most this many — about $0.05 and several minutes. More is
# another click, so the cost of each one stays small and visible.
MAX_PER_RUN = 50


class AnalysisRequest(BaseModel):
    """Exactly one of the two: specific jobs, or the newest `newest` unscored ones."""

    jobIds: list[str] | None = Field(default=None, min_length=1, max_length=MAX_PER_RUN)
    newest: int | None = Field(default=None, ge=1, le=MAX_PER_RUN)

    @model_validator(mode="after")
    def one_of(self) -> AnalysisRequest:
        if (self.jobIds is None) == (self.newest is None):
            raise ValueError("send either jobIds or newest")
        return self


class AnalysisRun(BaseModel):
    id: str
    status: Literal["running", "done", "failed"]
    # Every job in the run, so the board can mark which cards are waiting.
    jobIds: list[str]
    results: list[AnalysisOutcome] = Field(default_factory=list)
    error: str | None = None
    startedAt: datetime
    finishedAt: datetime | None = None
