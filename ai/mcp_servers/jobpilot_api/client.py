"""An HTTP client for `server`'s REST API — never a database client.

This is the AI tier's only route to structural data: jobs, matches, resumes and the
profile. The function surface here is the tool surface P7-01 exposes over stdio, so
that step wraps these calls in MCP tool definitions rather than rewriting them.

Server-side validation is authoritative. Nothing here decides anything; a server
error is surfaced with its message intact, because a swallowed 422 becomes an agent
that silently does nothing.
"""

from __future__ import annotations

from typing import Any

import httpx

from config.settings import settings

_token: str | None = None


class JobPilotApiError(RuntimeError):
    """A non-2xx from `server`, carrying the server's own message."""

    def __init__(self, status: int, detail: str) -> None:
        self.status = status
        self.detail = detail
        super().__init__(f"server returned {status}: {detail}")


class NotSignedIn(RuntimeError):
    """The AI tier has no credentials, so every endpoint is closed to it."""


async def _sign_in(client: httpx.AsyncClient) -> str:
    if not settings.jobpilot_email or not settings.jobpilot_password:
        raise NotSignedIn(
            "set JOBPILOT_EMAIL and JOBPILOT_PASSWORD in ai/.env — every server "
            "endpoint outside signup/login requires a bearer token"
        )
    response = await client.post(
        "/account/login",
        json={"email": settings.jobpilot_email, "password": settings.jobpilot_password},
    )
    _raise_for_status(response)
    return response.json()["accessToken"]


async def _request(method: str, path: str, **kwargs: Any) -> Any:
    """One round trip, signing in on demand and once more if the token has expired."""
    global _token

    async with httpx.AsyncClient(
        base_url=settings.jobpilot_api_url.rstrip("/"), timeout=30.0
    ) as client:
        if _token is None:
            _token = await _sign_in(client)

        response = await client.request(
            method, path, headers={"Authorization": f"Bearer {_token}"}, **kwargs
        )
        if response.status_code == 401:
            _token = await _sign_in(client)
            response = await client.request(
                method, path, headers={"Authorization": f"Bearer {_token}"}, **kwargs
            )

        _raise_for_status(response)
        return None if response.status_code == 204 else response.json()


def _raise_for_status(response: httpx.Response) -> None:
    if response.status_code < 400:
        return
    try:
        detail = response.json().get("detail", response.text)
    except ValueError:
        detail = response.text
    raise JobPilotApiError(response.status_code, str(detail)[:500])


# --- the tool surface --------------------------------------------------------


async def get_job(job_id: str) -> dict[str, Any]:
    return await _request("GET", f"/job/getJob/{job_id}")


async def get_job_description(job_id: str) -> dict[str, Any]:
    """The posting including `jdText`, which `GET /job/{id}` withholds — the
    dashboard never renders it and only the matching step needs it."""
    return await _request("GET", f"/job/getJobDescription/{job_id}")


async def list_new_jobs(limit: int = 50) -> list[dict[str, Any]]:
    return await _request("GET", "/job", params={"status": "new", "limit": limit})


async def get_profile() -> dict[str, Any]:
    return await _request("GET", "/profile/getProfile")


async def get_match(job_id: str) -> dict[str, Any]:
    return await _request("GET", f"/match/getMatch/{job_id}")


async def write_match(payload: dict[str, Any]) -> dict[str, Any]:
    """Score plus the present/missing/risk lists. The JD vector belongs in Atlas and
    is not part of this call."""
    return await _request("POST", "/match/writeMatch", json=payload)


async def get_base_resume() -> dict[str, Any]:
    return await _request("GET", "/resume/base")


async def store_resume(payload: dict[str, Any]) -> dict[str, Any]:
    """Rejected with a 422 if it names a keyword the user did not tick, and with a
    409 before the keyword gate has resolved. Both checks live on the server."""
    return await _request("POST", "/resume/storeResume", json=payload)


def reset_session() -> None:
    """Drop the cached token — for tests, and for a credentials change."""
    global _token
    _token = None
