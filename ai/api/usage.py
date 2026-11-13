"""Writing a run's model calls to the usage log on the API server.

Best effort, deliberately: the run's results are already stored by the time this is
called, and a usage record that could not be written must not turn a finished run
into a failed one. What is lost is logged here instead.
"""

from __future__ import annotations

import logging

import httpx

from config.llm import Usage
from mcp_servers.jobpilot_api import client
from mcp_servers.jobpilot_api.client import JobPilotApiError

logger = logging.getLogger(__name__)

# The server's limit on one batch.
BATCH = 500


async def store_usage(run_kind: str, run_id: str | None, usage: Usage) -> None:
    calls = [call.as_payload() for call in usage.records]
    if not calls:
        return
    try:
        for start in range(0, len(calls), BATCH):
            await client.record_usage(run_kind, run_id, calls[start : start + BATCH])
    except (JobPilotApiError, httpx.HTTPError) as error:
        logger.warning(
            "usage of %s run %s not recorded (%d calls): %s", run_kind, run_id, len(calls), error
        )
