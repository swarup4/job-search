"""P3-14 — what the parse step is allowed to write.

A capture is untrusted text and the model reading it is not authoritative. A title,
a company or a technology that is not in the captured page must not reach the board,
because a listing filter is only worth having if what it filters on came from the
posting.
"""

from __future__ import annotations

from typing import Any

import pytest

from agents import parsing
from agents.parsing import ParsedPosting

PAGE = (
    "# Platform Engineer\n\n"
    "Acme Corp — Bengaluru, Karnataka, India\n\n"
    "Requisition REQ-4471\n\n"
    "You will run our Kubernetes clusters and write Terraform for the AWS estate.\n"
)

DESCRIPTION = {"id": "d1", "jdText": PAGE, "url": "https://acme.example/jobs/platform"}


def answers(*replies: object):
    """Stand in for the model, one reply per call, in order."""
    queue = list(replies)

    async def fake(shape, prompt, *, system, max_tokens=2048):
        return queue.pop(0)

    return fake


class FakeClient:
    """Records what the agent tried to write, so a test can assert on the payload."""

    def __init__(self, description: dict[str, Any] | None = None) -> None:
        self.description = description or DESCRIPTION
        self.created: list[dict[str, Any]] = []
        self.linked: list[tuple[str, str]] = []
        self.statuses: list[tuple[str, str]] = []
        self.updates: list[dict[str, Any]] = []

    async def get_description(self, description_id: str) -> dict[str, Any]:
        return self.description

    async def create_job(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.created.append(payload)
        return {"id": "j1", "duplicate": False}

    async def link_description(self, description_id: str, job_id: str) -> dict[str, Any]:
        self.linked.append((description_id, job_id))
        return {}

    async def set_description_status(self, description_id: str, status: str) -> dict[str, Any]:
        self.statuses.append((description_id, status))
        return {}

    async def update_description(
        self, description_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        self.updates.append(payload)
        return {}


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch) -> FakeClient:
    stub = FakeClient()
    monkeypatch.setattr(parsing, "client", stub)
    return stub


def posting(**overrides: Any) -> ParsedPosting:
    base: dict[str, Any] = {
        "isPosting": True,
        "title": "Platform Engineer",
        "company": "Acme Corp",
        "location": "Bengaluru, India",
        "requirements": ["Kubernetes", "Terraform", "AWS"],
    }
    return ParsedPosting(**(base | overrides))


# --- the page decides --------------------------------------------------------


async def test_a_posting_in_the_page_is_written_and_linked(
    fake: FakeClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(parsing, "generate", answers(posting(refId="REQ-4471")))

    outcome = await parsing.parse_description("d1")

    assert outcome.parsed and outcome.jobId == "j1"
    written = fake.created[0]
    assert written["title"] == "Platform Engineer"
    assert written["company"] == "Acme Corp"
    assert written["source"] == "career_page"
    assert written["refId"] == "REQ-4471"
    assert fake.linked == [("d1", "j1")]


async def test_a_company_not_in_the_page_refuses_the_parse(
    fake: FakeClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(parsing, "generate", answers(posting(company="Globex")))

    outcome = await parsing.parse_description("d1")

    assert not outcome.parsed
    assert "company" in (outcome.reason or "")
    assert fake.created == []
    # Left `raw`: a page this model read badly is not a page that is not a posting.
    assert fake.statuses == []


async def test_a_technology_the_page_never_names_is_dropped(
    fake: FakeClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        parsing,
        "generate",
        answers(posting(requirements=["Kubernetes", "Kafka", "Terraform"])),
    )

    await parsing.parse_description("d1")

    assert "requirements" not in fake.created[0]
    assert fake.updates[0]["requirements"] == ["Kubernetes", "Terraform"]


async def test_a_requisition_id_the_page_never_shows_is_dropped(
    fake: FakeClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(parsing, "generate", answers(posting(refId="REQ-9999")))

    await parsing.parse_description("d1")

    assert "refId" not in fake.created[0]


async def test_a_shortened_location_still_parses(
    fake: FakeClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The page says Karnataka, the model says India. Same place, written shorter."""
    monkeypatch.setattr(parsing, "generate", answers(posting()))

    await parsing.parse_description("d1")

    assert fake.created[0]["location"] == "Bengaluru, India"


async def test_an_invented_city_is_dropped_rather_than_written(
    fake: FakeClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(parsing, "generate", answers(posting(location="Berlin, Germany")))

    await parsing.parse_description("d1")

    assert fake.created[0]["location"] == ""


async def test_a_restated_posting_is_capped(
    fake: FakeClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every token here is in the page, so only the cap stands between a model that
    restates the posting and a filter that every job matches."""
    stack = [f"Tech{n}" for n in range(40)]
    fake.description = {
        "id": "d1",
        "jdText": PAGE + " " + " ".join(stack),
        "url": "https://acme.example/jobs/platform",
    }
    monkeypatch.setattr(parsing, "generate", answers(posting(requirements=stack)))

    await parsing.parse_description("d1")

    assert len(fake.updates[0]["requirements"]) == parsing.MAX_STACK


# --- pages that are not postings ---------------------------------------------


async def test_a_listing_page_is_discarded_not_written(
    fake: FakeClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(parsing, "generate", answers(posting(isPosting=False)))

    outcome = await parsing.parse_description("d1")

    assert not outcome.parsed
    assert fake.created == []
    assert fake.statuses == [("d1", "discarded")]


async def test_an_empty_capture_never_reaches_the_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stub = FakeClient({"id": "d2", "jdText": "   ", "url": "https://acme.example/x"})
    monkeypatch.setattr(parsing, "client", stub)

    def explode(*args: Any, **kwargs: Any):
        raise AssertionError("an empty capture must not cost a generation")

    monkeypatch.setattr(parsing, "generate", explode)

    outcome = await parsing.parse_description("d2")

    assert not outcome.parsed
    assert stub.statuses == [("d2", "discarded")]


# --- a batch survives one bad page -------------------------------------------


async def test_one_failure_does_not_end_the_batch(monkeypatch: pytest.MonkeyPatch) -> None:
    stub = FakeClient()

    async def list_raw(limit: int = 50) -> list[dict[str, Any]]:
        return [{"id": "d1"}, {"id": "d2"}]

    calls = {"n": 0}

    async def get_description(description_id: str) -> dict[str, Any]:
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("server said no")
        return DESCRIPTION

    stub.list_raw_descriptions = list_raw  # type: ignore[attr-defined]
    stub.get_description = get_description  # type: ignore[method-assign]
    monkeypatch.setattr(parsing, "client", stub)
    monkeypatch.setattr(parsing, "generate", answers(posting()))

    outcomes = await parsing.parse_pending()

    assert [o.parsed for o in outcomes] == [False, True]
    assert "server said no" in (outcomes[0].reason or "")
