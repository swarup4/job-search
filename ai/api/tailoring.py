"""The Tailor resume button: one job, answered in the same request.

Unlike discovery and analysis this is not a background run — it is one LLM call and a
handful of reads, a few seconds end to end, so the page simply waits for the result.
"""

from __future__ import annotations

from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, status

from agents import tailoring
from agents.tailoring import NoBaseResume, NoCurrentRole, SelectionGateNotPassed
from api.discovery import Caller
from mcp_servers.jobpilot_api.client import JobPilotApiError

router = APIRouter(tags=["tailoring"])

EXPIRED = "Your session expired. Sign in again and retry."


@router.post("/{job_id}", status_code=status.HTTP_201_CREATED)
async def tailor(job_id: str, who: Caller) -> dict[str, Any]:
    try:
        return await tailoring.tailor(job_id)
    except (SelectionGateNotPassed, NoBaseResume) as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error
    except NoCurrentRole as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error
    except JobPilotApiError as error:
        if error.status == 401:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, EXPIRED) from error
        code = error.status if error.status < 500 else status.HTTP_502_BAD_GATEWAY
        raise HTTPException(code, error.detail) from error
    except httpx.HTTPError as error:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, f"could not reach the API server: {error}"
        ) from error
