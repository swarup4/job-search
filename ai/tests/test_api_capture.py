"""The Capture button's second call: a stored page read into a job."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from agents import parsing
from agents.parsing import ParseOutcome
from api import deps
from api.capture import service as capture
from config.llm import GenerationError
from main import create_app
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

    async def get_job(self, job_id: str) -> dict[str, Any]:
        return {
            "id": job_id,
            "title": "LLM Engineer",
            "company": "Visa",
            "techStack": ["AWS", "RAG"],
        }


@pytest.fixture
async def api(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[AsyncClient]:
    fake = FakeClient()
    monkeypatch.setattr(deps, "client", fake)
    monkeypatch.setattr(deps, "_verified", {})
    monkeypatch.setattr(capture, "client", fake)
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test/api") as http:
        yield http


def parse_with(monkeypatch: pytest.MonkeyPatch, outcome: Any) -> None:
    async def parse(description_id: str) -> ParseOutcome:
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(parsing, "parse_description", parse)


async def test_capture_needs_a_token(api: AsyncClient) -> None:
    assert (await api.post("/capture/d1")).status_code == 401


async def test_a_posting_comes_back_as_its_job(
    api: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    parse_with(monkeypatch, ParseOutcome(descriptionId="d1", parsed=True, jobId="j1"))

    body = (await api.post("/capture/d1", headers=AUTH)).json()

    assert body == {
        "parsed": True, "jobId": "j1", "duplicate": False, "title": "LLM Engineer",
        "company": "Visa", "technologies": 2, "reason": None,
    }  # fmt: skip


async def test_a_page_that_is_not_a_posting_says_why(
    api: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    parse_with(
        monkeypatch, ParseOutcome(descriptionId="d1", parsed=False, reason="not a single posting")
    )

    body = (await api.post("/capture/d1", headers=AUTH)).json()

    assert (body["parsed"], body["reason"]) == (False, "not a single posting")


async def test_a_model_that_will_not_answer_is_a_bad_gateway(
    api: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    parse_with(monkeypatch, GenerationError("would not produce a valid ParsedPosting"))

    assert (await api.post("/capture/d1", headers=AUTH)).status_code == 502
