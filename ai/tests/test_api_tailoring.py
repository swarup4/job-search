"""The Tailor resume endpoint: who may call it, and how each refusal reaches the page."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from agents.tailoring import NoBaseResume, NoCurrentRole, SelectionGateNotPassed
from api import discovery
from api import tailoring as tailoring_api
from api.main import create_app
from mcp_servers.jobpilot_api.client import JobPilotApiError

AUTH = {"Authorization": "Bearer good"}


class FakeClient:
    def __init__(self) -> None:
        self.token: str | None = None

    def set_token(self, token: str) -> None:
        self.token = token

    async def get_account(self) -> dict[str, Any]:
        if self.token != "good":
            raise JobPilotApiError(401, "invalid token")
        return {"id": "u1"}


@pytest.fixture(autouse=True)
def fake(monkeypatch: pytest.MonkeyPatch) -> FakeClient:
    client = FakeClient()
    monkeypatch.setattr(discovery, "client", client)
    monkeypatch.setattr(discovery, "_verified", {})
    return client


@pytest.fixture
async def api() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test/api/tailoring") as http:
        yield http


def tailor_with(monkeypatch: pytest.MonkeyPatch, outcome: Any) -> list[str]:
    """Replace the agent: answer `outcome`, or raise it when it is an exception."""
    calls: list[str] = []

    async def tailor(job_id: str) -> dict[str, Any]:
        calls.append(job_id)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(tailoring_api.tailoring, "tailor", tailor)
    return calls


async def test_tailoring_needs_a_token(api: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = tailor_with(monkeypatch, {})

    response = await api.post("/j1")

    assert response.status_code == 401
    assert calls == []


async def test_a_tailored_resume_is_returned(
    api: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = tailor_with(monkeypatch, {"id": "r1", "version": 1, "tex": "x\n"})

    response = await api.post("/j1", headers=AUTH)

    assert response.status_code == 201
    assert response.json()["id"] == "r1"
    assert calls == ["j1"]


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (SelectionGateNotPassed("the keyword gate for this job is 'pending'"), 409),
        (NoBaseResume("pick a template on the Resume screen first"), 409),
        (NoCurrentRole("the profile has no work experience to tailor"), 422),
    ],
)
async def test_a_refusal_carries_its_reason(
    api: AsyncClient, monkeypatch: pytest.MonkeyPatch, error: Exception, code: int
) -> None:
    tailor_with(monkeypatch, error)

    response = await api.post("/j1", headers=AUTH)

    assert response.status_code == code
    assert response.json()["detail"] == str(error)


async def test_a_token_that_expires_mid_request_says_so(
    api: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    tailor_with(monkeypatch, JobPilotApiError(401, "expired"))

    response = await api.post("/j1", headers=AUTH)

    assert response.status_code == 401
    assert response.json()["detail"] == tailoring_api.EXPIRED


async def test_a_server_failure_is_a_bad_gateway(
    api: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    tailor_with(monkeypatch, JobPilotApiError(500, "boom"))

    response = await api.post("/j1", headers=AUTH)

    assert response.status_code == 502
