import asyncio
import json

from pydantic import ValidationError

from config.error_log import ERROR_LOG_PATH, append_error
from modules.error_log.models import ErrorEntry, ErrorReport


def _read() -> list[ErrorEntry]:
    if not ERROR_LOG_PATH.is_file():
        return []
    entries: list[ErrorEntry] = []
    for line in ERROR_LOG_PATH.read_text(encoding="utf-8").splitlines():
        try:
            entries.append(ErrorEntry.model_validate(json.loads(line)))
        except (json.JSONDecodeError, ValidationError):
            # A line cut short by a crash mid-write; the rest of the file is still good.
            continue
    return entries


async def list_errors(limit: int) -> list[ErrorEntry]:
    entries = await asyncio.to_thread(_read)
    return entries[::-1][:limit]


async def report_error(report: ErrorReport) -> None:
    await asyncio.to_thread(
        append_error, "web", report.message, detail=report.detail, context=report.context
    )


async def clear_errors() -> None:
    await asyncio.to_thread(ERROR_LOG_PATH.unlink, missing_ok=True)
