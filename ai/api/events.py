"""A background run's progress as server-sent events — shared by analysis and match runs.

Every event is kept for the life of the run, so opening the stream is also how a page
finds your latest run: it replays from `run_started`, which carries the run itself.
Events that already existed when the stream opened are marked `replay: true`, so a page
joining late can show them without announcing them again. `Last-Event-ID` resumes after
a dropped connection. The stream closes after `run_done`.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Callable
from typing import Any

from fastapi import Request
from fastapi.responses import StreamingResponse

# A comment line this often keeps an idle stream from being closed as dead while a
# slow model call is in flight.
KEEPALIVE_SECONDS = 15


class EventLog:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []
        # Replaced on every event: each waiting stream holds the old one, which is set.
        self._tick = asyncio.Event()

    def emit(self, event: dict[str, Any]) -> None:
        self.events.append(event)
        tick, self._tick = self._tick, asyncio.Event()
        tick.set()

    def stream(
        self, request: Request, last_event_id: str | None, is_current: Callable[[], bool]
    ) -> StreamingResponse:
        """`is_current` turns false once a newer run replaces this one."""
        start = int(last_event_id) + 1 if last_event_id and last_event_id.isdigit() else 0

        async def events() -> AsyncIterator[str]:
            index = start
            # Everything before this was emitted before the page connected.
            joined_at = len(self.events)
            while True:
                tick = self._tick
                if not is_current():
                    return
                while index < len(self.events):
                    event = {**self.events[index], "replay": index < joined_at}
                    data = json.dumps(event, default=str)
                    yield f"id: {index}\nevent: {event['type']}\ndata: {data}\n\n"
                    index += 1
                    if event["type"] == "run_done":
                        return
                if await request.is_disconnected():
                    return
                try:
                    await asyncio.wait_for(tick.wait(), KEEPALIVE_SECONDS)
                except TimeoutError:
                    yield ": keepalive\n\n"

        return StreamingResponse(
            events(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
