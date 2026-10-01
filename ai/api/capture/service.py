"""The extension's Capture button, second half: read the stored page into a job.

    curl -X POST http://127.0.0.1:8001/api/capture/<descriptionId> -H "Authorization: Bearer <token>"

The page is stored first (`POST /job-description` on the API server), so a model that
fails or times out here loses nothing — the capture stays `raw` and can be read again.
One model call: title, company, location, the four details and the tech stack, each
checked against the page. Analyze then has only the embedding and the match to do.
"""

from __future__ import annotations

import httpx

from agents import parsing
from api.capture.models import CaptureResult
from config.errors import BadGateway, Unauthorized, Upstream
from config.llm import GenerationError
from mcp_servers.jobpilot_api import client
from mcp_servers.jobpilot_api.client import JobPilotApiError

EXPIRED = "Your session expired. Sign in again and capture the page again."


async def process_capture(description_id: str) -> CaptureResult:
    try:
        outcome = await parsing.parse_description(description_id)
        if not outcome.parsed or outcome.jobId is None:
            return CaptureResult(parsed=False, reason=outcome.reason)
        job = await client.get_job(outcome.jobId)
    except JobPilotApiError as error:
        if error.status == 401:
            raise Unauthorized(EXPIRED) from error
        raise Upstream(error.status, error.detail) from error
    except GenerationError as error:
        raise BadGateway(str(error)) from error
    except httpx.HTTPError as error:
        raise BadGateway(f"could not reach the model or the API server: {error}") from error
    return CaptureResult(
        parsed=True,
        jobId=outcome.jobId,
        duplicate=outcome.duplicate,
        title=job.get("title"),
        company=job.get("company"),
        technologies=len(job.get("techStack") or []),
    )
