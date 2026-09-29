"""The extension's Capture button, second half: read the stored page into a job.

    curl -X POST http://127.0.0.1:8001/api/capture/<descriptionId> -H "Authorization: Bearer <token>"

The page is stored first (`POST /job-description` on the API server), so a model that
fails or times out here loses nothing — the capture stays `raw` and can be read again.
One model call: title, company, location, the four details and the tech stack, each
checked against the page. Analyze then has only the embedding and the match to do.
"""

from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from agents import parsing
from api.discovery import Caller
from config.llm import GenerationError
from mcp_servers.jobpilot_api import client
from mcp_servers.jobpilot_api.client import JobPilotApiError

router = APIRouter(tags=["capture"])

EXPIRED = "Your session expired. Sign in again and capture the page again."


class CaptureResult(BaseModel):
    """What the popup shows: the job made from the page, or why there is none."""

    parsed: bool
    jobId: str | None = None
    duplicate: bool = False
    title: str | None = None
    company: str | None = None
    technologies: int = 0
    reason: str | None = None


@router.post("/{description_id}", response_model=CaptureResult)
async def process_capture(description_id: str, who: Caller) -> CaptureResult:
    try:
        outcome = await parsing.parse_description(description_id)
        if not outcome.parsed or outcome.jobId is None:
            return CaptureResult(parsed=False, reason=outcome.reason)
        job = await client.get_job(outcome.jobId)
    except JobPilotApiError as error:
        if error.status == 401:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, EXPIRED) from error
        code = error.status if error.status < 500 else status.HTTP_502_BAD_GATEWAY
        raise HTTPException(code, error.detail) from error
    except GenerationError as error:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(error)) from error
    except httpx.HTTPError as error:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, f"could not reach the model or the API server: {error}"
        ) from error
    return CaptureResult(
        parsed=True,
        jobId=outcome.jobId,
        duplicate=outcome.duplicate,
        title=job.get("title"),
        company=job.get("company"),
        technologies=len(job.get("techStack") or []),
    )
