"""CE-12 — pass/fail checks made in code before a posting is compared.

A gate may fail a posting only on something the posting said. And a gated posting must
never reach the compare call: that is the whole saving.
"""

from __future__ import annotations

from typing import Any

import pytest

from agents import matching
from agents.gates import check_gates
from agents.matching import Brief, Requirement

TARGETS = {"locations": ["India"], "workMode": "hybrid", "minExperience": 8}
INDIA = {"location": "Bengaluru, Karnataka", "country": "India", "cities": ["Bengaluru"]}
ABROAD = {"location": "Austin, TX", "country": "United States", "cities": ["Austin"]}


def brief(**fields: Any) -> Brief:
    return Brief(requirements=[], **fields)


def test_a_posting_inside_every_target_passes() -> None:
    assert check_gates(brief(minYears=10, workMode="hybrid"), INDIA, TARGETS) is None


def test_a_posting_that_states_nothing_passes() -> None:
    """Silence is not a mismatch: no place, no mode and no years is compared as before."""
    assert check_gates(brief(), {"location": ""}, TARGETS) is None


def test_an_unread_country_is_not_failed_on_its_city() -> None:
    assert check_gates(brief(), {"location": "Whitefield", "country": None}, TARGETS) is None


def test_a_posting_in_another_country_fails_on_location() -> None:
    gate = check_gates(brief(), ABROAD, TARGETS)

    assert gate is not None and gate.key == "gate-location"
    assert "Austin, TX" in gate.detail and "India" in gate.detail


def test_a_city_target_matches_as_a_whole_word() -> None:
    targets = {"locations": ["Pune"]}
    pune = {"location": "Pune, Maharashtra", "country": "India", "cities": ["Pune"]}
    assert check_gates(brief(), pune, targets) is None
    assert check_gates(brief(), INDIA, targets).key == "gate-location"


def test_a_different_work_mode_fails_only_when_the_posting_states_one() -> None:
    assert check_gates(brief(workMode="remote"), INDIA, TARGETS).key == "gate-work-mode"
    assert check_gates(brief(), INDIA | {"workMode": "on_site"}, TARGETS).key == "gate-work-mode"
    assert check_gates(brief(workMode="remote"), INDIA, {"workMode": None}) is None


def test_a_posting_below_the_minimum_experience_fails() -> None:
    gate = check_gates(brief(minYears=3), INDIA, TARGETS)

    assert gate.key == "gate-experience"
    assert "3+ years" in gate.detail and "8" in gate.detail
    assert check_gates(brief(minYears=8), INDIA, TARGETS) is None


def test_no_saved_targets_gate_nothing() -> None:
    assert check_gates(brief(minYears=1, workMode="remote"), ABROAD, {}) is None
    assert check_gates(brief(minYears=1, workMode="remote"), ABROAD, None) is None


# --- a gated posting is never compared ----------------------------------------


class FakeApi:
    def __init__(self, job: dict[str, Any], preferences: dict[str, Any]) -> None:
        self.job = {"id": "j1", "title": "Engineer", "company": "Acme", **job}
        self.preferences = preferences
        self.written: list[dict[str, Any]] = []
        self.asked_for_inventory = False

    async def get_job(self, job_id: str) -> dict[str, Any]:
        return self.job

    async def get_description_for_job(self, job_id: str) -> dict[str, Any]:
        return {"id": "d1", "jdText": "x"}

    async def get_profile(self) -> dict[str, Any]:
        return {"name": "A", "work": [], "skill": []}

    async def get_preferences(self) -> dict[str, Any]:
        return self.preferences

    async def get_skill_inventory(self) -> None:
        self.asked_for_inventory = True
        raise AssertionError("a gated posting built an inventory")

    async def write_match(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.written.append(payload)
        return payload


async def test_a_gated_posting_gets_a_match_without_a_model_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = FakeApi(ABROAD, TARGETS)
    monkeypatch.setattr(matching, "jobpilot_api", api)

    async def refuse(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("the model was called for a gated posting")

    monkeypatch.setattr(matching, "generate", refuse)
    posting = Brief(
        requirements=[
            Requirement(key="python", label="Python", kind="tech", mentions=2, evidence="Python")
        ]
    )

    match = await matching.rectify("j1", posting)

    assert match["gate"] == "gate-location"
    assert (match["score"], match["present"], match["missing"]) == (0, [], [])
    assert [risk["title"] for risk in match["risks"]] == ["Outside your locations"]
    # Nothing a model produced, so no model is named and nothing is offered to select.
    assert match["modelName"] is None
    assert not api.asked_for_inventory
