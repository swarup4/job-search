"""The AI tier's half of the shared error log — the server owns the other half and
the endpoint that reads it, so the format here must match `server/config/error_log.py`."""

import json
import logging
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import config  # noqa: F401 — imported for its .env load

ERROR_LOG_PATH = Path(
    os.environ.get(
        "ERROR_LOG_PATH", Path(__file__).resolve().parents[2] / "logs" / "errors.jsonl"
    )
)

_TRACEBACK = logging.Formatter()


def append_error(
    source: str,
    message: str,
    *,
    level: str = "error",
    detail: str | None = None,
    context: dict[str, Any] | None = None,
) -> None:
    entry = {
        "id": uuid.uuid4().hex[:12],
        "at": datetime.now(UTC).isoformat(),
        "source": source,
        "level": level,
        "message": message,
        "detail": detail,
        "context": context or {},
    }
    ERROR_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    # One write per entry, in append mode, so two tiers writing at once interleave
    # whole lines rather than characters.
    with ERROR_LOG_PATH.open("a", encoding="utf-8") as file:
        file.write(json.dumps(entry, default=str) + "\n")


class ErrorLogHandler(logging.Handler):
    def __init__(self, source: str) -> None:
        super().__init__(level=logging.ERROR)
        self.source = source

    def emit(self, record: logging.LogRecord) -> None:
        try:
            detail = _TRACEBACK.formatException(record.exc_info) if record.exc_info else None
            append_error(
                self.source,
                record.getMessage(),
                level=record.levelname.lower(),
                detail=detail,
                context={"logger": record.name},
            )
        except Exception:  # noqa: BLE001 — logging must never raise into the caller
            self.handleError(record)
