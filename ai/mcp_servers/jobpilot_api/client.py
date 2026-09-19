"""An HTTP client for `server`'s REST API — never a database client.

The tier holds no credentials: it acts as whoever is signed in at the UI, which
forwards their JWT through `set_token`. A server error is surfaced with its message
intact, because a swallowed 422 becomes an agent that silently does nothing.
"""

from __future__ import annotations

import os
from contextvars import ContextVar
from typing import Any

import httpx

import config  # noqa: F401 — imported for its .env load

# The AI tier reaches structural data only over HTTP. It holds no database URI.
JOBPILOT_API_URL = os.environ.get("JOBPILOT_API_URL", "http://127.0.0.1:8000/api")

# A ContextVar rather than a module global: two callers must never see each other's
# token, which a shared global cannot promise once anything runs concurrently.
_token: ContextVar[str | None] = ContextVar("jobpilot_token", default=None)


class JobPilotApiError(RuntimeError):
    """A refused call, carrying the server's own message. `status` is 401 when no
    token was supplied, which is the answer the server would have given anyway."""

    def __init__(self, status: int, detail: str) -> None:
        self.status = status
        self.detail = detail
        super().__init__(f"server returned {status}: {detail}")


def set_token(token: str) -> None:
    """The signed-in user's JWT, forwarded from the UI. Every call afterwards in this
    task acts as that user."""
    _token.set(token)


async def _request(method: str, path: str, **kwargs: Any) -> Any:
    """One round trip as the caller's user.

    A 401 is not retried: the tier has nothing to sign in with, and the refresh token
    belongs to whoever forwarded the JWT."""
    token = _token.get()
    if not token:
        raise JobPilotApiError(401, "no JWT — call set_token() with the signed-in user's token")

    async with httpx.AsyncClient(base_url=JOBPILOT_API_URL.rstrip("/"), timeout=30.0) as client:
        response = await client.request(
            method, path, headers={"Authorization": f"Bearer {token}"}, **kwargs
        )

    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        raise JobPilotApiError(response.status_code, str(detail)[:500])
    return None if response.status_code == 204 else response.json()


# --- the tool surface --------------------------------------------------------


async def get_job(job_id: str) -> dict[str, Any]:
    return await _request("GET", f"/job/getJob/{job_id}")


async def create_job(payload: dict[str, Any]) -> dict[str, Any]:
    """`{id, duplicate}` — a repeat posting comes back as the row already stored."""
    return await _request("POST", "/job/createJob", json=payload)


async def get_description_for_job(job_id: str) -> dict[str, Any] | None:
    return await _request("GET", f"/job-description/for-job/{job_id}")


async def get_description(description_id: str) -> dict[str, Any]:
    return await _request("GET", f"/job-description/{description_id}")


async def list_raw_descriptions(limit: int = 50) -> list[dict[str, Any]]:
    """Captures nobody has turned into a posting yet — the parse queue."""
    return await _request("GET", "/job-description", params={"status": "raw", "limit": limit})


async def link_description(description_id: str, job_id: str) -> dict[str, Any]:
    return await _request("POST", f"/job-description/link/{description_id}/{job_id}")


async def update_description(description_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    return await _request("PATCH", f"/job-description/{description_id}", json=payload)


async def set_description_status(description_id: str, status: str) -> dict[str, Any]:
    return await _request(
        "PATCH", f"/job-description/status/{description_id}", params={"new_status": status}
    )


async def get_profile() -> dict[str, Any]:
    return await _request("GET", "/profile/getProfile")


async def get_match(job_id: str) -> dict[str, Any]:
    return await _request("GET", f"/match/getMatch/{job_id}")


async def write_match(payload: dict[str, Any]) -> dict[str, Any]:
    return await _request("POST", "/match/writeMatch", json=payload)


async def get_base_resume() -> dict[str, Any]:
    return await _request("GET", "/resume/base")


async def store_resume(payload: dict[str, Any]) -> dict[str, Any]:
    """Rejected with a 422 if it names a keyword the user did not tick, and with a
    409 before the keyword gate has resolved. Both checks live on the server."""
    return await _request("POST", "/resume/storeResume", json=payload)
