"""The Analyze button: what each step may write, that one failure spares the rest, and
the endpoint that runs it."""

from __future__ import annotations

import asyncio
import json
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
        self.embeddings: list[list[float]] = []
        # What the match step was handed: None means it extracted for itself.
        self.rectified_with: list[list[Any] | None] = []

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

    async def extract(jd_text: str) -> list[matching.Requirement]:
        return [
            matching.Requirement(key="aws", label="AWS", kind="tech", mentions=1, evidence="AWS"),
            matching.Requirement(
                key="6-10-years", label="6-10 years", kind="qualification", mentions=1, evidence="x"
            ),
            matching.Requirement(key="rag", label="RAG", kind="tech", mentions=1, evidence="RAG"),
        ]

    async def rectify(job_id: str, requirements: list[Any] | None = None) -> dict[str, Any]:
        client.rectified_with.append(requirements)
        return {"score": 72, "present": [{"label": "AWS"}], "missing": [{"label": "RAG"}]}

    monkeypatch.setattr(analysis, "generate", proposes)
    monkeypatch.setattr(matching, "extract_requirements", extract)
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
    assert fake.embeddings == [[0.1, 0.2, 0.3]]
    # Only the technologies, and the match reuses the same extraction.
    assert {"techStack": ["AWS", "RAG"]} in fake.job_updates
    assert [len(handed or []) for handed in fake.rectified_with] == [3]


async def test_details_never_overwrite_what_the_board_gave(fake: FakeClient) -> None:
    await analysis.analyze("j1")
    # jobType came from the board, and the invented salary is dropped by the check.
    assert fake.job_updates[0] == {"experienceBand": "6-10 years", "workMode": "hybrid"}


async def test_a_job_already_matched_is_skipped_whole(fake: FakeClient) -> None:
    fake.match = {"score": 64}
    fake.job["techStack"] = ["AWS"]
    outcome = await analysis.analyze("j1")
    assert outcome.skipped == "already analyzed"
    assert outcome.score == 64
    assert outcome.steps == {}
    assert fake.embeddings == [] and fake.job_updates == []


async def test_a_matched_job_without_a_stack_gets_only_the_stack(fake: FakeClient) -> None:
    """Jobs analyzed before the tech stack existed: one extraction, no second match."""
    fake.match = {"score": 64}
    fake.description = {"id": "d1", "jdText": JD, "hasEmbedding": True}
    outcome = await analysis.analyze("j1")

    assert outcome.skipped is None
    assert outcome.steps["techStack"].note == "2 technologies"
    assert outcome.steps["match"].note == "already matched"
    assert fake.rectified_with == []
    assert outcome.score == 64


async def test_a_stack_already_read_is_not_read_again(fake: FakeClient) -> None:
    """An empty stack is an answer too — a posting that names no technology."""
    fake.job["techStack"] = []
    outcome = await analysis.analyze("j1")

    assert outcome.steps["techStack"].note == "already read"
    assert fake.rectified_with == [None]
    assert not any("techStack" in update for update in fake.job_updates)


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

    monkeypatch.setattr(fake, "update_job", refused)
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

    async def analyze_many(job_ids, on_result=None, at_once=2, on_event=None):
        seen.append(job_ids)
        await release.wait()
        for job_id in job_ids:
            on_event({"type": "step_started", "jobId": job_id, "step": "details"})
            on_event({"type": "step", "jobId": job_id, "step": "details", "ok": True, "note": "x"})
            on_result(analysis.AnalysisOutcome(jobId=job_id, score=60))

    monkeypatch.setattr(analysis, "analyze_many", analyze_many)
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test/api/runs") as http:
        yield http, release, seen


async def finish() -> None:
    task = analysis_api._slot.task
    assert task is not None
    await task


GOOD = {"Authorization": "Bearer good"}


async def test_one_job_from_its_card(api) -> None:
    http, release, _ = api
    started = await http.post("/analysis/start", json={"jobIds": ["j9"]}, headers=GOOD)
    assert started.status_code == 202, started.text
    assert started.json()["jobIds"] == ["j9"]

    release.set()
    await finish()
    run = analysis_api._slot.run.model_dump(mode="json")
    assert run["status"] == "done"
    assert [r["jobId"] for r in run["results"]] == ["j9"]


async def test_the_newest_new_jobs_in_bulk(api) -> None:
    http, release, seen = api
    started = await http.post("/analysis/start", json={"newest": 2}, headers=GOOD)
    assert started.json()["jobIds"] == ["n1", "n2"]
    release.set()
    await finish()
    assert seen == [["n1", "n2"]]


async def test_exactly_one_way_to_choose_jobs(api) -> None:
    http, _, _ = api
    for body in ({}, {"jobIds": ["a"], "newest": 3}, {"newest": 500}):
        assert (await http.post("/analysis/start", json=body, headers=GOOD)).status_code == 422


async def test_one_run_at_a_time_and_a_second_start_joins_it(api) -> None:
    """Yours already running: the start answers that run, so the page follows it."""
    http, release, _ = api
    first = (await http.post("/analysis/start", json={"jobIds": ["j1"]}, headers=GOOD)).json()
    again = await http.post("/analysis/start", json={"jobIds": ["j2"]}, headers=GOOD)
    other = await http.post(
        "/analysis/start", json={"jobIds": ["j3"]}, headers={"Authorization": "Bearer other"}
    )
    release.set()
    await finish()

    assert again.status_code == 200 and again.json()["id"] == first["id"]
    assert other.status_code == 409


def parse_stream(body: str) -> list[tuple[str, str, dict[str, Any]]]:
    """(id, event, data) for each server-sent event, keep-alive comments skipped."""
    events = []
    for block in body.strip().split("\n\n"):
        fields = dict(
            line.split(": ", 1) for line in block.splitlines() if not line.startswith(":")
        )
        if fields:
            events.append((fields["id"], fields["event"], json.loads(fields["data"])))
    return events


async def test_every_step_is_streamed_and_the_stream_ends_with_the_run(api) -> None:
    http, release, _ = api
    await http.post("/analysis/start", json={"jobIds": ["j9"]}, headers=GOOD)
    release.set()
    await finish()

    response = await http.get("/analysis/events", headers=GOOD)

    assert response.headers["content-type"].startswith("text/event-stream")
    events = parse_stream(response.text)
    assert [kind for _, kind, _ in events] == [
        "run_started", "step_started", "step", "job_done", "run_done",
    ]  # fmt: skip
    # The first event is the run itself — how a page finds its latest run.
    assert events[0][2]["run"]["jobIds"] == ["j9"]
    assert events[3][2]["score"] == 60
    done = events[-1][2]
    assert (done["status"], done["error"], done["finishedAt"] is not None) == ("done", None, True)


async def test_events_from_before_the_stream_opened_are_marked_replay(api) -> None:
    """A page joining late shows them, but does not announce them again."""
    http, release, _ = api
    await http.post("/analysis/start", json={"jobIds": ["j9"]}, headers=GOOD)
    release.set()
    await finish()

    events = parse_stream((await http.get("/analysis/events", headers=GOOD)).text)

    assert all(data["replay"] for _, _, data in events)


async def test_a_reconnect_resumes_after_the_last_event_seen(api) -> None:
    http, release, _ = api
    await http.post("/analysis/start", json={"jobIds": ["j9"]}, headers=GOOD)
    release.set()
    await finish()

    response = await http.get("/analysis/events", headers={**GOOD, "Last-Event-ID": "2"})

    assert [kind for _, kind, _ in parse_stream(response.text)] == ["job_done", "run_done"]


async def test_another_account_cannot_follow_the_run(api) -> None:
    http, release, _ = api
    await http.post("/analysis/start", json={"jobIds": ["j9"]}, headers=GOOD)
    release.set()
    await finish()

    response = await http.get("/analysis/events", headers={"Authorization": "Bearer other"})

    assert response.status_code == 204


async def test_needs_a_token(api) -> None:
    http, _, _ = api
    assert (await http.post("/analysis/start", json={"newest": 1})).status_code == 401


async def test_a_job_whose_stack_was_read_skips_the_details(
    fake: FakeClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A capture reads details and stack in one call, so Analyze pays for neither again."""
    fake.job["techStack"] = ["AWS"]

    async def must_not_run(*args: Any, **kwargs: Any) -> JobDetails:
        raise AssertionError("the details model was called")

    monkeypatch.setattr(analysis, "generate", must_not_run)
    outcome = await analysis.analyze("j1")

    assert outcome.steps["details"].note == "already read"
    assert outcome.steps["techStack"].note == "already read"
    assert outcome.steps["embedding"].ok and outcome.steps["match"].ok
