"""The scoring run behind the header's Refresh: every unscored job, one at a time."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from agents import matching
from api import deps
from api.scoring import service as scoring_api
from main import create_app
from mcp_servers.jobpilot_api.client import JobPilotApiError

AUTH = {"Authorization": "Bearer good"}


class FakeClient:
    """The server as the run sees it: jobs leave `unscored` once they have a match."""

    def __init__(self, unscored: list[str]) -> None:
        self.token: str | None = None
        self.unscored = list(unscored)
        self.pages: list[int] = []
        self.relevant: list[bool] = []

    def set_token(self, token: str) -> None:
        self.token = token

    async def get_account(self) -> dict[str, Any]:
        if self.token not in {"good", "other"}:
            raise JobPilotApiError(401, "invalid token")
        return {"id": "u1" if self.token == "good" else "u2"}

    async def list_unscored_jobs(self, limit: int, relevant: bool = False) -> list[dict[str, Any]]:
        return (await self.unscored_jobs(limit, relevant))["jobs"]

    async def unscored_jobs(self, limit: int, relevant: bool = False) -> dict[str, Any]:
        self.pages.append(limit)
        # A scoring run only ever asks for the jobs inside the caller's search targets.
        self.relevant.append(relevant)
        jobs = [{"id": job_id, "title": f"Job {job_id}"} for job_id in self.unscored[:limit]]
        return {"total": len(self.unscored), "jobs": jobs}


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch) -> FakeClient:
    client = FakeClient([f"j{n}" for n in range(1, 4)])
    monkeypatch.setattr(deps, "client", client)
    monkeypatch.setattr(deps, "_verified", {})
    monkeypatch.setattr(scoring_api, "client", client)
    monkeypatch.setattr(scoring_api, "_slot", scoring_api._Slot())

    async def score_job(job_id: str) -> dict[str, Any]:
        client.unscored.remove(job_id)
        return {"jobId": job_id, "score": 70}

    monkeypatch.setattr(matching, "score_job", score_job)
    return client


@pytest.fixture
async def api(fake: FakeClient) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test/api/runs") as http:
        yield http


async def finish() -> None:
    task = scoring_api._slot.task
    assert task is not None
    await task


def kinds(body: str) -> list[str]:
    return [
        json.loads(line[len("data: ") :])["type"]
        for line in body.splitlines()
        if line.startswith("data: ")
    ]


async def test_a_run_needs_a_token(api: AsyncClient) -> None:
    assert (await api.post("/scoring/start")).status_code == 401


async def test_every_unscored_job_is_scored(api: AsyncClient, fake: FakeClient) -> None:
    started = await api.post("/scoring/start", headers=AUTH)
    assert started.status_code == 202
    await finish()

    run = scoring_api._slot.run.model_dump(mode="json")

    assert run["status"] == "done"
    assert (run["scored"], run["failed"]) == (3, 0)
    assert [r["jobId"] for r in run["results"]] == ["j1", "j2", "j3"]
    assert fake.unscored == []


async def test_it_keeps_asking_past_one_page(
    api: AsyncClient, fake: FakeClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake.unscored = [f"j{n}" for n in range(1, 6)]
    monkeypatch.setattr(scoring_api, "BATCH", 2)

    await api.post("/scoring/start", headers=AUTH)
    await finish()

    assert scoring_api._slot.run.scored == 5


async def test_a_run_stops_at_its_cap_and_reports_what_is_left(
    api: AsyncClient, fake: FakeClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CE-07: a run is a bounded spend. The jobs past the cap are left for the next
    run, not dropped, and the run says how many."""
    fake.unscored = [f"j{n}" for n in range(1, 8)]
    monkeypatch.setattr(scoring_api, "MAX_JOBS", 3)

    await api.post("/scoring/start", headers=AUTH)
    await finish()

    run = scoring_api._slot.run
    assert (run.status, run.scored, run.remaining) == ("done", 3, 4)
    assert fake.unscored == ["j4", "j5", "j6", "j7"]


async def test_a_run_scores_only_jobs_inside_the_search_targets(
    api: AsyncClient, fake: FakeClient
) -> None:
    """The catalogue is shared. Every listing a run asks for is the relevant one."""
    await api.post("/scoring/start", headers=AUTH)
    await finish()

    assert fake.relevant and all(fake.relevant)


async def test_a_failing_job_is_tried_once_and_the_rest_still_scored(
    api: AsyncClient, fake: FakeClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """It stays unscored, so without the guard it would come back in every page."""

    async def score_job(job_id: str) -> dict[str, Any]:
        if job_id == "j2":
            raise matching.NoDescription("no job description is stored for this job")
        fake.unscored.remove(job_id)
        return {"score": 70}

    monkeypatch.setattr(matching, "score_job", score_job)
    await api.post("/scoring/start", headers=AUTH)
    await finish()

    run = scoring_api._slot.run.model_dump(mode="json")
    assert (run["status"], run["scored"], run["failed"]) == ("done", 2, 1)
    assert "no job description" in run["results"][1]["error"]
    # Still unscored, so it counts among what the next run will take.
    assert run["remaining"] == 1


async def test_refresh_during_a_run_returns_that_run(
    api: AsyncClient, fake: FakeClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    release = asyncio.Event()

    async def slow(job_id: str) -> dict[str, Any]:
        await release.wait()
        fake.unscored.remove(job_id)
        return {"score": 70}

    monkeypatch.setattr(matching, "score_job", slow)
    first = (await api.post("/scoring/start", headers=AUTH)).json()
    again = await api.post("/scoring/start", headers=AUTH)
    other = await api.post("/scoring/start", headers={"Authorization": "Bearer other"})
    release.set()
    await finish()

    assert again.status_code == 200 and again.json()["id"] == first["id"]
    assert other.status_code == 409


async def test_progress_streams_and_ends_with_the_run(api: AsyncClient) -> None:
    await api.post("/scoring/start", headers=AUTH)
    await finish()

    body = (await api.get("/scoring/events", headers=AUTH)).text

    assert kinds(body) == ["run_started"] + ["job_started", "job_done"] * 3 + ["run_done"]


async def test_a_dead_token_ends_the_run(api: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def expired(job_id: str) -> dict[str, Any]:
        raise JobPilotApiError(401, "expired")

    monkeypatch.setattr(matching, "score_job", expired)
    await api.post("/scoring/start", headers=AUTH)
    await finish()

    run = scoring_api._slot.run.model_dump(mode="json")
    assert run["status"] == "failed"
    assert run["error"] == scoring_api.EXPIRED
