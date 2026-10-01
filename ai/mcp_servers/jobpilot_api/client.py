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


async def list_unscored_jobs(limit: int) -> list[dict[str, Any]]:
    """The caller's newest jobs with no match yet — what "Analyze new jobs" takes."""
    body = await _request("GET", "/match/unscored", params={"limit": limit})
    return body["jobs"]


async def update_job(job_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """A partial update — only the fields sent change."""
    return await _request("PATCH", f"/job/updateJob/{job_id}", json=payload)


async def create_job(payload: dict[str, Any]) -> dict[str, Any]:
    """`{id, duplicate}` — a repeat posting comes back as the row already stored."""
    return await _request("POST", "/job/createJob", json=payload)


async def get_description_for_job(job_id: str) -> dict[str, Any] | None:
    return await _request("GET", f"/job-description/for-job/{job_id}")


async def get_description(description_id: str) -> dict[str, Any]:
    return await _request("GET", f"/job-description/{description_id}")


async def description_stored(url: str) -> bool:
    """Whether a description already exists for this exact URL — how a re-run learns
    a posting is stored without fetching it from the board again."""
    rows = await _request("GET", "/job-description", params={"url": url, "limit": 1})
    return bool(rows)


async def store_description_embedding(description_id: str, vector: list[float]) -> dict[str, Any]:
    """The JD's vector, embedded here — the server only stores it and indexes it."""
    return await _request(
        "PUT", f"/job-description/embedding/{description_id}", json={"embedding": vector}
    )


async def store_brief(description_id: str, brief: dict[str, Any]) -> dict[str, Any]:
    """The posting read into requirements and constraints, stored on its description —
    which every later read of that description then carries as `brief`."""
    return await _request("PUT", f"/job-description/storeBrief/{description_id}", json=brief)


async def get_account() -> dict[str, Any]:
    """The signed-in account. Doubles as the check that a forwarded token is real."""
    return await _request("GET", "/account/getAccount")


async def create_description(payload: dict[str, Any]) -> dict[str, Any]:
    """`{id, duplicate}` — the same url and text twice comes back as the row stored."""
    return await _request("POST", "/job-description", json=payload)


async def list_raw_descriptions(limit: int = 50) -> list[dict[str, Any]]:
    """Captures nobody has turned into a posting yet — the parse queue."""
    return await _request("GET", "/job-description", params={"status": "raw", "limit": limit})


async def link_description(description_id: str, job_id: str) -> dict[str, Any]:
    return await _request("POST", f"/job-description/link/{description_id}/{job_id}")


async def set_description_status(description_id: str, status: str) -> dict[str, Any]:
    return await _request(
        "PATCH", f"/job-description/status/{description_id}", params={"new_status": status}
    )


async def get_preferences() -> dict[str, Any]:
    """The account's saved Search targets — titles, locations, page cap. An account
    that never saved any gets the server's defaults, never a 404."""
    return await _request("GET", "/preference")


async def list_career_sources(enabled: bool | None = None) -> list[dict[str, Any]]:
    params = {} if enabled is None else {"enabled": str(enabled).lower()}
    return await _request("GET", "/career-source", params=params)


async def record_source_result(source_id: str, result: dict[str, Any]) -> dict[str, Any]:
    return await _request("PUT", f"/career-source/result/{source_id}", json=result)


async def get_profile() -> dict[str, Any]:
    return await _request("GET", "/profile/getProfile")


async def reindex_profile() -> dict[str, Any]:
    """Re-cut My Details into chunks. Returns the index stats. Text only — the server
    never embeds anything, which is why this leaves chunks pending."""
    return await _request("POST", "/profile/reindex")


async def get_skill_inventory() -> dict[str, Any] | None:
    """The profile read into skills, or None before the first one is built."""
    try:
        return await _request("GET", "/skill-inventory/getInventory")
    except JobPilotApiError as error:
        if error.status == 404:
            return None
        raise


async def replace_skill_inventory(inventory: dict[str, Any]) -> dict[str, Any]:
    return await _request("PUT", "/skill-inventory/replaceInventory", json=inventory)


async def list_pending_chunks(limit: int = 200) -> list[dict[str, Any]]:
    """Chunks with no vector yet — everything this tier still owes the index."""
    return await _request("GET", "/resume-chunk/pending", params={"limit": limit})


async def store_chunk_embeddings(embeddings: list[dict[str, Any]]) -> dict[str, Any]:
    """One request for a whole profile's vectors. Refused outright if any chunk id is
    not the caller's or no longer exists, rather than partly applied."""
    return await _request("PUT", "/resume-chunk/embeddings", json={"embeddings": embeddings})


async def search_chunks(vector: list[float], limit: int = 50) -> list[dict[str, Any]]:
    """`$vectorSearch` over the caller's own chunks. The vector is embedded here; the
    server runs the query, because this tier has no database URI."""
    return await _request("POST", "/resume-chunk/search", json={"vector": vector, "limit": limit})


async def chunk_stats() -> dict[str, Any]:
    return await _request("GET", "/resume-chunk/stats")


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
