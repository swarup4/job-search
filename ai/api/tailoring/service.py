"""The Tailor resume button: one job, answered in the same request.

Unlike discovery and analysis this is not a background run — it is one LLM call and a
handful of reads, a few seconds end to end, so the page simply waits for the result.
"""

from __future__ import annotations

from typing import Any

import httpx

from agents import tailoring
from agents.tailoring import NoBaseResume, NoCurrentRole, SelectionGateNotPassed
from config.errors import BadGateway, Conflict, Invalid, Unauthorized, Upstream
from mcp_servers.jobpilot_api.client import JobPilotApiError

EXPIRED = "Your session expired. Sign in again and retry."


async def tailor(job_id: str) -> dict[str, Any]:
    try:
        return await tailoring.tailor(job_id)
    except (SelectionGateNotPassed, NoBaseResume) as error:
        raise Conflict(str(error)) from error
    except NoCurrentRole as error:
        raise Invalid(str(error)) from error
    except JobPilotApiError as error:
        if error.status == 401:
            raise Unauthorized(EXPIRED) from error
        raise Upstream(error.status, error.detail) from error
    except httpx.HTTPError as error:
        raise BadGateway(f"could not reach the API server: {error}") from error
