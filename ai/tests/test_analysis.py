"""The Analyze button: what each step may write, that one failure spares the rest, and
the endpoint that runs it."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from agents import analysis, matching
from agents.analysis import JobDetails, verify_details
from api import analysis as analysis_api
from api import discovery
from api.main import create_app
from mcp_servers.jobpilot_api.client import JobPilotApiError

JD = (
    "## LLM Engineer\n\n"
    "Build RAG pipelines on AWS. You bring 6-10 years of experience.\n\n"
    "This is a hybrid role in Bengaluru, full-time. <b>Apply</b> now."
)


class FakeClient:
    def __init__(
        self, job: dict[str, Any] | None = None, description: dict[str, Any] | None = None
    ) -> None:
        self.job = job or {
            "id": "j1",
            "title": "LLM Engineer",
            "company": "Acme",
            "jobType": "full_time",
        }
        self.description = description if description is not None else {"id": "d1", "jdText": JD}
        self.match: dict[str, Any] | None = None
        self.job_updates: list[dict[str, Any]] = []
        self.description_updates: list[dict[str, Any]] = []
        self.embeddings: list[list[float]] = []

    async def get_job(self, job_id: str) -> dict[str, Any]:
        return self.job

    async def get_description_for_job(self, job_id: str) -> dict[str, Any] | None:
        return self.description or None

    async def get_match(self, job_id: str) -> dict[str, Any]:
        if self.match is None:
            raise JobPilotApiError(404, "no match")
        return self.match

    async def update_job(self, job_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.job_updates.append(payload)
        return {}

    async def update_description(
        self, description_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        self.description_updates.append(payload)
        return {}

    async def store_description_embedding(
        self, description_id: str, vector: list[float]
    ) -> dict[str, Any]:
        self.embeddings.append(vector)
        return {}


class FakeVoyage:
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2, 0.3] for _ in texts]


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch) -> FakeClient:
    client = FakeClient()
    monkeypatch.setattr(analysis, "client", client)
    monkeypatch.setattr(analysis, "VoyageEmbeddings", FakeVoyage)

    async def proposes(shape, prompt, *, system, max_tokens=2048):
        return JobDetails(
            experience="6-10 years", salary="40 LPA", workMode="hybrid", jobType="contract"
        )

    async def rectify(job_id: str) -> dict[str, Any]:
        return {
            "score": 72,
            "present": [{"label": "AWS"}],
            "missing": [{"label": "RAG"}, {"label": "AWS"}],
        }

    monkeypatch.setattr(analysis, "generate", proposes)
    monkeypatch.setattr(matching, "rectify", rectify)
    return client


# --- pure helpers -----------------------------------------------------------------


def test_only_what_the_posting_says_is_kept() -> None:
    kept = verify_details(
        JobDetails(experience="6-10 years", salary="40 LPA", workMode="hybrid", jobType="contract"),
        JD,
    )
    assert kept.experience == "6-10 years"
    # Not in the text: an invented salary, and a job type the page contradicts.
    assert kept.salary is None
    assert kept.jobType is None
    assert kept.workMode == "hybrid"


def test_a_work_mode_needs_a_word_that_says_so() -> None:
    kept = verify_details(JobDetails(workMode="remote"), "Bengaluru office, Monday to Friday.")
    assert kept.workMode is None


# --- one job ------------------------------------------------------------------------


async def test_every_step_writes_its_own_field(fake: FakeClient) -> None:
    outcome = await analysis.analyze("j1")

    assert outcome.score == 72
    assert all(step.ok for step in outcome.steps.values()), outcome.steps
    assert not any("htmlString" in update for update in fake.description_updates)
    assert fake.embeddings == [[0.1, 0.2, 0.3]]
    requirements = next(u["requirements"] for u in fake.description_updates if "requirements" in u)
    assert requirements == ["AWS", "RAG"]


async def test_details_never_overwrite_what_the_board_gave(fake: FakeClient) -> None:
    await analysis.analyze("j1")
    # jobType came from the board, and the invented salary is dropped by the check.
    assert fake.job_updates == [{"experienceBand": "6-10 years", "workMode": "hybrid"}]


async def test_a_job_already_matched_is_skipped_whole(fake: FakeClient) -> None:
    fake.match = {"score": 64}
    outcome = await analysis.analyze("j1")
    assert outcome.skipped == "already analyzed"
    assert outcome.score == 64
    assert outcome.steps == {}
    assert fake.embeddings == [] and fake.job_updates == [] and fake.description_updates == []


async def test_an_embedded_description_keeps_its_vector(fake: FakeClient) -> None:
    fake.description = {"id": "d1", "jdText": JD, "hasEmbedding": True}
    outcome = await analysis.analyze("j1")
    assert fake.embeddings == []
    assert outcome.steps["embedding"].note == "already embedded"
    assert outcome.steps["match"].ok


async def test_known_details_skip_the_model(
    fake: FakeClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake.job.update(experienceBand="8 years", salaryText="₹40 LPA", workMode="remote")

    async def must_not_run(*args: Any, **kwargs: Any) -> JobDetails:
        raise AssertionError("the details model was called")

    monkeypatch.setattr(analysis, "generate", must_not_run)
    outcome = await analysis.analyze("j1")
    assert outcome.steps["details"].note == "all details already known"


async def test_a_job_without_a_description_is_reported_not_analyzed(fake: FakeClient) -> None:
    fake.description = {}
    outcome = await analysis.analyze("j1")
    assert outcome.error is not None
    assert outcome.steps == {}


async def test_one_failing_step_spares_the_others(
    fake: FakeClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    class Down:
        async def embed_documents(self, texts: list[str]) -> list[list[float]]:
            raise RuntimeError("voyage unavailable")

    monkeypatch.setattr(analysis, "VoyageEmbeddings", Down)
    outcome = await analysis.analyze("j1")
    assert outcome.steps["embedding"].ok is False
    assert "voyage unavailable" in (outcome.steps["embedding"].note or "")
    assert outcome.steps["match"].ok and outcome.steps["details"].ok


async def test_a_dead_token_stops_the_job(
    fake: FakeClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def refused(description_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        raise JobPilotApiError(401, "expired")

    monkeypatch.setattr(fake, "update_description", refused)
    with pytest.raises(JobPilotApiError):
        await analysis.analyze("j1")


# --- the endpoint -------------------------------------------------------------------


class ApiFake:
    def __init__(self) -> None:
        self.token: str | None = None
        self.new_jobs = [{"id": "n1"}, {"id": "n2"}]

    def set_token(self, token: str) -> None:
        self.token = token

    async def get_account(self) -> dict[str, Any]:
        if self.token not in {"good": 1, "other": 1}:
            raise JobPilotApiError(401, "invalid token")
        return {"id": "u1" if self.token == "good" else "u2"}

    async def list_unscored_jobs(self, limit: int) -> list[dict[str, Any]]:
        return self.new_jobs[:limit]


@pytest.fixture
async def api(
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[tuple[AsyncClient, asyncio.Event, list]]:
    fake_api = ApiFake()
    monkeypatch.setattr(discovery, "client", fake_api)
    monkeypatch.setattr(discovery, "_verified", {})
    monkeypatch.setattr(analysis_api, "client", fake_api)
    monkeypatch.setattr(analysis_api, "_slot", analysis_api._Slot())

    release = asyncio.Event()
    seen: list[list[str]] = []

    async def analyze_many(job_ids, on_result=None, at_once=2):
        seen.append(job_ids)
        await release.wait()
        for job_id in job_ids:
            on_result(analysis.AnalysisOutcome(jobId=job_id, score=60))

    monkeypatch.setattr(analysis, "analyze_many", analyze_many)
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test/api/analysis") as http:
        yield http, release, seen


async def finish() -> None:
    task = analysis_api._slot.task
    assert task is not None
    await task


GOOD = {"Authorization": "Bearer good"}


async def test_one_job_from_its_card(api) -> None:
    http, release, _ = api
    started = await http.post("/run", json={"jobIds": ["j9"]}, headers=GOOD)
    assert started.status_code == 202, started.text
    assert started.json()["jobIds"] == ["j9"]

    release.set()
    await finish()
    run = (await http.get("/run", headers=GOOD)).json()
    assert run["status"] == "done"
    assert [r["jobId"] for r in run["results"]] == ["j9"]


async def test_the_newest_new_jobs_in_bulk(api) -> None:
    http, release, seen = api
    started = await http.post("/run", json={"newest": 2}, headers=GOOD)
    assert started.json()["jobIds"] == ["n1", "n2"]
    release.set()
    await finish()
    assert seen == [["n1", "n2"]]


async def test_exactly_one_way_to_choose_jobs(api) -> None:
    http, _, _ = api
    for body in ({}, {"jobIds": ["a"], "newest": 3}, {"newest": 500}):
        assert (await http.post("/run", json=body, headers=GOOD)).status_code == 422


async def test_one_run_at_a_time_and_only_its_owner_sees_it(api) -> None:
    http, release, _ = api
    await http.post("/run", json={"jobIds": ["j1"]}, headers=GOOD)
    assert (await http.post("/run", json={"jobIds": ["j2"]}, headers=GOOD)).status_code == 409
    release.set()
    await finish()
    assert (await http.get("/run", headers={"Authorization": "Bearer other"})).json() is None


async def test_needs_a_token(api) -> None:
    http, _, _ = api
    assert (await http.post("/run", json={"newest": 1})).status_code == 401
