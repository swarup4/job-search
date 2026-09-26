"""The Run discovery endpoint: who may start a run, one run at a time, and what a
run that loses its token reports."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from api import discovery, settings
from api.main import create_app
from mcp_servers.jobpilot_api.client import JobPilotApiError
from sources.base import DEFAULT_WORKDAY_MAX_PAGES

SOURCES = [
    {"id": "s1", "name": "Accenture", "platform": "workday", "config": {}},
    {"id": "s2", "name": "Zoom", "platform": "workday", "config": {}},
]


class FakeClient:
    """The server as far as the endpoint sees it: a token maps to an account."""

    def __init__(self) -> None:
        self.accounts = {"good": "u1", "other": "u2"}
        self.sources = list(SOURCES)
        self.token: str | None = None
        self.account_checks = 0
        self.preferences = {
            "roles": ["GenAI Engineer", "LLM"],
            "locations": ["Bengaluru"],
            "workMode": "hybrid",
            "minExperience": 6,
        }

    def set_token(self, token: str) -> None:
        self.token = token

    async def get_account(self) -> dict[str, Any]:
        self.account_checks += 1
        if self.token not in self.accounts:
            raise JobPilotApiError(401, "invalid token")
        return {"id": self.accounts[self.token]}

    async def list_career_sources(self, enabled: bool | None = None) -> list[dict[str, Any]]:
        return self.sources

    async def get_preferences(self) -> dict[str, Any]:
        return self.preferences


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch) -> FakeClient:
    client = FakeClient()
    monkeypatch.setattr(discovery, "client", client)
    monkeypatch.setattr(discovery, "_slot", discovery._Slot())
    monkeypatch.setattr(discovery, "_verified", {})
    return client


@pytest.fixture
async def api(fake: FakeClient) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test/api/discovery") as http:
        yield http


class Held(asyncio.Event):
    """Holds a run open until set, and records the filters the scrape was handed."""

    def __init__(self) -> None:
        super().__init__()
        self.filters: list[Any] = []


def scrape_with(monkeypatch: pytest.MonkeyPatch, behaviour: Any) -> Held:
    """Replace the scrape itself."""
    release = Held()

    async def run_all(sources, filters=None, on_result=None):
        release.filters.append(filters)
        await release.wait()
        return await behaviour(sources, on_result)

    monkeypatch.setattr(discovery.scrape, "run_all", run_all)
    return release


async def reports_each(sources, on_result):
    for source in sources:
        on_result(source["name"], {"fetched": 20, "matched": 3, "new": 2, "duplicate": 1})


async def finish() -> None:
    task = discovery._slot.task
    assert task is not None
    await task


async def test_no_token_is_refused(api: AsyncClient) -> None:
    assert (await api.post("/run")).status_code == 401


async def test_a_token_the_server_rejects_is_refused(api: AsyncClient) -> None:
    response = await api.post("/run", headers={"Authorization": "Bearer forged"})
    assert response.status_code == 401


async def test_a_run_reports_every_company(
    api: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    release = scrape_with(monkeypatch, reports_each)
    started = await api.post("/run", headers={"Authorization": "Bearer good"})
    assert started.status_code == 202
    assert started.json()["status"] == "running"
    assert started.json()["companies"] == 2

    release.set()
    await finish()

    run = (await api.get("/run", headers={"Authorization": "Bearer good"})).json()
    assert run["status"] == "done"
    assert [r["name"] for r in run["results"]] == ["Accenture", "Zoom"]
    assert run["results"][0]["new"] == 2
    assert run["finishedAt"] is not None


async def test_one_run_at_a_time(api: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    release = scrape_with(monkeypatch, reports_each)
    await api.post("/run", headers={"Authorization": "Bearer good"})

    second = await api.post("/run", headers={"Authorization": "Bearer good"})
    assert second.status_code == 409

    release.set()
    await finish()


async def test_another_account_does_not_see_the_run(
    api: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    release = scrape_with(monkeypatch, reports_each)
    await api.post("/run", headers={"Authorization": "Bearer good"})
    release.set()
    await finish()

    seen = await api.get("/run", headers={"Authorization": "Bearer other"})
    assert seen.status_code == 200
    assert seen.json() is None


async def test_a_token_that_expires_mid_run_says_so(
    api: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def expires(sources, on_result):
        on_result("Accenture", {"new": 5})
        raise JobPilotApiError(401, "token expired")

    release = scrape_with(monkeypatch, expires)
    await api.post("/run", headers={"Authorization": "Bearer good"})
    release.set()
    await finish()

    run = (await api.get("/run", headers={"Authorization": "Bearer good"})).json()
    assert run["status"] == "failed"
    assert run["error"] == discovery.EXPIRED
    assert [r["name"] for r in run["results"]] == ["Accenture"]


async def test_nothing_to_run_is_refused(api: AsyncClient, fake: FakeClient) -> None:
    fake.sources = []
    response = await api.post("/run", headers={"Authorization": "Bearer good"})
    assert response.status_code == 422
    assert "seed" in response.json()["detail"]


async def test_polling_does_not_recheck_the_token_every_time(
    api: AsyncClient, fake: FakeClient
) -> None:
    for _ in range(5):
        response = await api.get("/run", headers={"Authorization": "Bearer good"})
        assert response.status_code == 200
    assert fake.account_checks == 1


async def test_a_token_is_rechecked_once_the_cache_lapses(
    api: AsyncClient, fake: FakeClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    await api.get("/run", headers={"Authorization": "Bearer good"})
    monkeypatch.setattr(discovery, "VERIFIED_FOR", 0.0)
    await api.get("/run", headers={"Authorization": "Bearer good"})
    assert fake.account_checks == 2


async def test_a_rejected_token_is_not_cached(api: AsyncClient, fake: FakeClient) -> None:
    for _ in range(2):
        assert (
            await api.get("/run", headers={"Authorization": "Bearer forged"})
        ).status_code == 401
    assert fake.account_checks == 2


async def test_settings_report_what_is_configured(fake: FakeClient) -> None:
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test/api") as http:
        assert (await http.get("/settings")).status_code == 401
        body = (await http.get("/settings", headers={"Authorization": "Bearer good"})).json()
    assert body["scrape"]["userAgent"] == settings.USER_AGENT
    assert body["models"]["generation"]
    assert body["models"]["embeddings"]


async def test_a_run_uses_the_saved_search_targets(
    api: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    release = scrape_with(monkeypatch, reports_each)
    started = (await api.post("/run", headers={"Authorization": "Bearer good"})).json()
    release.set()
    await finish()

    assert started["filters"]["titles"] == ["GenAI Engineer", "LLM"]
    assert started["filters"]["locations"] == ["Bengaluru"]
    assert release.filters[0].titles == ["GenAI Engineer", "LLM"]
    assert release.filters[0].workdayMaxPages == DEFAULT_WORKDAY_MAX_PAGES
