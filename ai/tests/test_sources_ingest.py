"""The one write path every adapter shares, the filters in front of it, and the run
that reports on both."""

from __future__ import annotations

from typing import Any

import pytest

from mcp_servers.jobpilot_api.client import JobPilotApiError
from sources import base, run
from sources.base import Filters, Harvest, Posting, dedup_hash, ingest
from sources.http import RobotsDisallowed

FILTERS = Filters(titles=["LLM"], locations=["India"], workdayMaxPages=5)

POSTING = Posting(
    refId="R00334988",
    title="Senior LLM Engineer",
    company="Accenture",
    location="Bengaluru, India",
    jobType="full_time",
    listingUrl="https://accenture.wd103.myworkdayjobs.com/AccentureCareers/job/Bengaluru/x",
    html="<p><b>Role:</b> build RAG pipelines</p><ul><li>Python</li></ul>",
)


class FakeClient:
    def __init__(
        self,
        job_duplicate: bool = False,
        has_description: bool = False,
        fail_with: int | None = None,
    ) -> None:
        self.job_duplicate = job_duplicate
        self.has_description = has_description
        self.fail_with = fail_with
        self.jobs: list[dict[str, Any]] = []
        self.descriptions: list[dict[str, Any]] = []
        self.linked: list[tuple[str, str]] = []

    async def create_job(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self.fail_with:
            raise JobPilotApiError(self.fail_with, "refused")
        self.jobs.append(payload)
        return {"id": "j1", "duplicate": self.job_duplicate}

    async def get_description_for_job(self, job_id: str) -> dict[str, Any] | None:
        return {"id": "d0"} if self.has_description else None

    async def create_description(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.descriptions.append(payload)
        return {"id": "d1", "duplicate": False}

    async def link_description(self, description_id: str, job_id: str) -> dict[str, Any]:
        self.linked.append((description_id, job_id))
        return {}


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch) -> FakeClient:
    client = FakeClient()
    monkeypatch.setattr(base, "client", client)
    return client


async def test_a_new_posting_writes_job_description_and_link(fake: FakeClient) -> None:
    assert await ingest(POSTING) is True

    job = fake.jobs[0]
    assert job["source"] == "career_page"
    assert job["refId"] == "R00334988"
    assert job["dedupHash"] == dedup_hash(POSTING)

    description = fake.descriptions[0]
    assert description["region"] == "feed"
    assert "**Role:** build RAG pipelines" in description["markdown"]
    assert "<p>" not in description["markdown"]
    assert description["links"] == [POSTING.listingUrl]
    assert fake.linked == [("d1", "j1")]


async def test_the_boards_country_is_sent_with_the_job(fake: FakeClient) -> None:
    """The server parses `location` only when the board gave no country of its own."""
    await ingest(POSTING.model_copy(update={"country": "India"}))
    await ingest(POSTING)

    assert [job["country"] for job in fake.jobs] == ["India", None]


async def test_a_stored_posting_is_left_alone(fake: FakeClient) -> None:
    fake.job_duplicate = fake.has_description = True
    assert await ingest(POSTING) is False
    assert fake.descriptions == []


async def test_a_stored_posting_missing_its_description_is_repaired(fake: FakeClient) -> None:
    fake.job_duplicate = True
    assert await ingest(POSTING) is False
    assert fake.linked == [("d1", "j1")]


def test_the_same_req_id_at_two_companies_is_two_jobs() -> None:
    other = POSTING.model_copy(update={"company": "Genpact"})
    assert dedup_hash(POSTING) != dedup_hash(other)


def test_titles_are_matched_on_word_boundaries() -> None:
    filters = Filters(titles=["AI", "Machine Learning"], locations=["India"], workdayMaxPages=5)
    assert filters.title_wanted("AI / ML Engineer")
    assert filters.title_wanted("Lead ai Architect")
    assert filters.title_wanted("Machine Learning Scientist")
    assert not filters.title_wanted("Maintenance Lead")
    assert not filters.title_wanted("Email Marketing Specialist")


def adapter_returning(harvest: Harvest):
    async def fetch(source: dict[str, Any], http: Any, is_stored: Any, filters: Any) -> Harvest:
        return harvest

    return fetch


async def test_a_run_counts_new_duplicate_and_failed(
    monkeypatch: pytest.MonkeyPatch, fake: FakeClient
) -> None:
    monkeypatch.setitem(
        run.ADAPTERS,
        "workday",
        adapter_returning(Harvest(fetched=40, failed=1, postings=[POSTING])),
    )
    result = await run.run_source({"platform": "workday"}, None, FILTERS)  # type: ignore[arg-type]
    assert result == {"fetched": 40, "matched": 1, "new": 1, "duplicate": 0, "failed": 1}


async def test_postings_skipped_as_stored_count_as_duplicates(
    monkeypatch: pytest.MonkeyPatch, fake: FakeClient
) -> None:
    monkeypatch.setitem(
        run.ADAPTERS, "workday", adapter_returning(Harvest(fetched=60, known=9, postings=[POSTING]))
    )
    result = await run.run_source({"platform": "workday"}, None, FILTERS)  # type: ignore[arg-type]
    assert result == {"fetched": 60, "matched": 10, "new": 1, "duplicate": 9, "failed": 0}


async def test_robots_is_reported_as_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    async def refuse(source: dict[str, Any], http: Any, is_stored: Any, filters: Any) -> Harvest:
        raise RobotsDisallowed("https://zoom.wd5.myworkdayjobs.com/Zoom/")

    monkeypatch.setitem(run.ADAPTERS, "workday", refuse)
    result = await run.run_source({"platform": "workday"}, None, FILTERS)  # type: ignore[arg-type]
    assert result["blocked"] is True
    assert result["new"] == 0


async def test_a_missing_token_stops_the_run(
    monkeypatch: pytest.MonkeyPatch, fake: FakeClient
) -> None:
    fake.fail_with = 401
    monkeypatch.setitem(run.ADAPTERS, "workday", adapter_returning(Harvest(postings=[POSTING])))
    with pytest.raises(JobPilotApiError):
        await run.run_source({"platform": "workday"}, None, FILTERS)  # type: ignore[arg-type]


async def test_a_refused_write_is_counted_and_the_run_goes_on(
    monkeypatch: pytest.MonkeyPatch, fake: FakeClient
) -> None:
    fake.fail_with = 422
    monkeypatch.setitem(
        run.ADAPTERS, "workday", adapter_returning(Harvest(postings=[POSTING, POSTING]))
    )
    result = await run.run_source({"platform": "workday"}, None, FILTERS)  # type: ignore[arg-type]
    assert result["failed"] == 2
    assert "refused" in result["error"]


def test_unsaved_or_empty_preferences_fall_back_to_the_defaults() -> None:
    assert Filters.from_preferences(None).titles == base.DEFAULT_TITLES
    partial = Filters.from_preferences({"roles": ["LLM"], "locations": []})
    assert partial.titles == ["LLM"]
    assert partial.locations == base.DEFAULT_LOCATIONS
    assert partial.workdayMaxPages == base.DEFAULT_WORKDAY_MAX_PAGES
