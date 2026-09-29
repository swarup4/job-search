"""`/errorLog` — the shared error file every tier appends to, read newest first."""

from __future__ import annotations

import logging
from pathlib import Path

from httpx import AsyncClient

from config import error_log


async def test_error_log_needs_a_token(client: AsyncClient) -> None:
    assert (await client.get("/errorLog")).status_code == 401


async def test_reports_and_log_records_read_back_newest_first(signed_in: AsyncClient) -> None:
    # Through the root handler `configure_logging` installs, as the middleware's would.
    try:
        raise ValueError("boom")
    except ValueError:
        logging.getLogger("tests.error_log").exception("unhandled error on GET /x")

    report = {"message": "Could not compile the PDF.", "context": {"status": 422}}
    assert (await signed_in.post("/errorLog", json=report)).status_code == 204

    entries = (await signed_in.get("/errorLog")).json()
    assert [(e["source"], e["message"]) for e in entries] == [
        ("web", "Could not compile the PDF."),
        ("server", "unhandled error on GET /x"),
    ]
    assert entries[0]["context"] == {"status": 422}
    assert "ValueError: boom" in entries[1]["detail"]


async def test_a_torn_line_is_skipped(signed_in: AsyncClient, log_file: Path) -> None:
    error_log.append_error("ai", "scoring run failed")
    with log_file.open("a") as file:
        file.write('{"id": "half')

    entries = (await signed_in.get("/errorLog")).json()
    assert [e["message"] for e in entries] == ["scoring run failed"]


async def test_clear_empties_the_log(signed_in: AsyncClient) -> None:
    error_log.append_error("ai", "scoring run failed")
    assert (await signed_in.delete("/errorLog")).status_code == 204
    assert (await signed_in.get("/errorLog")).json() == []
