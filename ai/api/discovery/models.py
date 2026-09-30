from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from sources.base import Filters


class CompanyResult(BaseModel):
    name: str
    fetched: int = 0
    matched: int = 0
    new: int = 0
    duplicate: int = 0
    failed: int = 0
    blocked: bool = False
    # Not scraped: the run's limit was reached before this company's turn.
    skipped: bool = False
    # Of `matched`, how many came in on a skill in the description, not a role in the title.
    bySkill: int = 0
    error: str | None = None


class DiscoveryRequest(BaseModel):
    """`limit` stops the run once that many new jobs are stored. Omitted, every enabled
    company is scraped in full, filtered by your Search targets."""

    limit: int | None = Field(default=None, ge=1, le=500)


class DiscoveryRun(BaseModel):
    id: str
    status: Literal["running", "done", "failed"]
    companies: int
    # How many new jobs this run was asked for; null means every one it finds.
    limit: int | None = None
    # The Search targets this run was started with, read once at the start — so a
    # change saved mid-run applies to the next run, and the screen can show which.
    filters: Filters
    results: list[CompanyResult] = Field(default_factory=list)
    error: str | None = None
    startedAt: datetime
    finishedAt: datetime | None = None
