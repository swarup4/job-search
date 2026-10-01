"""The Tailor resume button: one job, answered in the same request.

Unlike discovery and analysis this is not a background run — it is one LLM call and a
handful of reads, a few seconds end to end, so the page simply waits for the result.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from agents import tailoring
from agents.tailoring import NoBaseResume, NoCurrentRole, SelectionGateNotPassed
from config.errors import BadGateway, Conflict, Invalid, Unauthorized, Upstream
from config.llm import GenerationError, track_usage
from mcp_servers.jobpilot_api.client import JobPilotApiError

logger = logging.getLogger(__name__)

EXPIRED = "Your session expired. Sign in again and retry."


async def tailor(job_id: str) -> dict[str, Any]:
    try:
        with track_usage() as usage:
            resume = await tailoring.tailor(job_id)
        logger.info("tailoring %s: tokens %s", job_id, usage.summary())
        return resume
    except (SelectionGateNotPassed, NoBaseResume) as error:
        raise Conflict(str(error)) from error
    except NoCurrentRole as error:
        raise Invalid(str(error)) from error
    except JobPilotApiError as error:
        if error.status == 401:
            raise Unauthorized(EXPIRED) from error
        raise Upstream(error.status, error.detail) from error
    except GenerationError as error:
        raise BadGateway(str(error)) from error
    except httpx.HTTPError as error:
        raise BadGateway(f"could not reach the model or the API server: {error}") from error
