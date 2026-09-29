from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ErrorEntry(BaseModel):
    id: str
    at: datetime
    source: Literal["server", "ai", "web"]
    level: str
    message: str
    detail: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)


class ErrorReport(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    detail: str | None = Field(default=None, max_length=20000)
    context: dict[str, str | int | None] = Field(default_factory=dict)
