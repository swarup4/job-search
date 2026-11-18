"""EV-03 — the evaluation's arithmetic, and a run of it with the model faked.

The runner's value is that its numbers can be trusted when a prompt changes, so the
numbers are tested here against cases small enough to count by hand.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from agents import inventory, matching
from agents.details import JobDetails
from agents.inventory import DraftInventory, DraftSkill
from agents.matching import BriefDraft, Comparison, ExtractedKeyword, Verdict
from eval import dataset, runner
from eval.metrics import Counts, detail_counts, rates, requirement_counts, verdict_counts

SAMPLE = Path(__file__).resolve().parents[1] / "eval" / "sample"


# --- metrics ------------------------------------------------------------------


def test_requirements_are_matched_ignoring_case_and_punctuation() -> None:
    counts = requirement_counts(
        ["Kubernetes", "Node.js", "Terraform"], ["kubernetes", "node js", "Kafka"]
    )

    assert (counts.required, counts.found, counts.found_right) == (3, 3, 2)
    scores = rates(counts)
    assert scores["requirementPrecision"] == pytest.approx(0.6667, abs=1e-4)
    assert scores["requirementRecall"] == pytest.approx(0.6667, abs=1e-4)


def test_a_detail_the_posting_does_not_state_is_right_only_when_left_empty() -> None:
    expected = JobDetails(experience="6+ years", workMode="hybrid")
    found = JobDetails(experience="6+  Years", workMode="hybrid", salary="40 LPA")

    counts = detail_counts(expected, found)

    # Experience matches after normalising; the invented salary is the one miss.
    assert (counts.details, counts.details_right) == (4, 3)


def test_a_wrong_present_is_counted_apart_from_a_wrong_missing() -> None:
    counts = verdict_counts(
        expected_present=["AWS", "Python"],
        expected_missing=["Kubernetes", "Terraform"],
        got_present=["AWS", "Kubernetes"],
        got_missing=["Python", "Terraform"],
    )

    assert (counts.judged, counts.judged_right) == (4, 2)
    scores = rates(counts)
    assert scores["wrongPresentRate"] == 0.5  # Kubernetes, of the two it lacks
    assert scores["wrongMissingRate"] == 0.5  # Python, of the two it has
    assert scores["verdictAccuracy"] == 0.5


def test_a_requirement_the_brief_never_found_is_not_a_wrong_verdict() -> None:
    """It is a recall miss, counted there. Scoring it here would count it twice."""
    counts = verdict_counts(["AWS"], ["Kubernetes"], got_present=["AWS"], got_missing=[])

    assert (counts.judged, counts.labelled_missing, counts.wrong_present) == (1, 0, 0)


def test_nothing_to_measure_reads_as_unknown_not_as_perfect() -> None:
    assert rates(Counts())["wrongPresentRate"] is None


def test_counts_add_before_any_rate_is_taken() -> None:
    """A mean of per-posting rates would let a small posting outvote a large one."""
    small = requirement_counts(["A"], [])
    large = requirement_counts([f"R{n}" for n in range(9)], [f"R{n}" for n in range(9)])

    assert rates(small + large)["requirementRecall"] == 0.9


# --- the labelled set ----------------------------------------------------------


def test_the_sample_set_loads_and_its_labels_are_in_its_postings() -> None:
    """A label naming something the posting never says would score the model down for
    being right."""
    labelled = dataset.load(SAMPLE)

    assert len(labelled.postings) == 1 and len(labelled.profiles) == 1
    for posting in labelled.postings:
        for label in posting.requirements:
            assert label.lower() in posting.jdText.lower()
        for profile_id in posting.verdicts:
            assert labelled.profile(profile_id) is not None


def test_a_repeated_id_is_refused(tmp_path: Path) -> None:
    posting = {"id": "p1", "jdText": "x", "requirements": []}
    for name in ("a.json", "b.json"):
        (tmp_path / name).write_text(json.dumps({"postings": [posting]}), encoding="utf-8")

    with pytest.raises(ValueError, match="p1"):
        dataset.load(tmp_path)


# --- a run, with the model faked ------------------------------------------------


@pytest.fixture
def model(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """A model that finds three of the four requirements and gets one verdict wrong."""
    asked: list[str] = []

    def keyword(label: str, evidence: str) -> ExtractedKeyword:
        return ExtractedKeyword(label=label, kind="tech", evidence=evidence)

    async def generate(shape: Any, prompt: str, **kwargs: Any) -> Any:
        asked.append(shape.__name__)
        if shape is BriefDraft:
            return BriefDraft(
                requirements=[
                    keyword("Kubernetes", "run our Kubernetes clusters"),
                    keyword("Terraform", "write Terraform for the AWS estate"),
                    keyword("Python", "Python for tooling and automation"),
                ],
                seniority=None,
                minYears=6,
                locationRule=None,
                workMode="hybrid",
                experience="6+ years",
                salary=None,
                jobType="full_time",
            )
        if shape is DraftInventory:
            return DraftInventory(
                skills=[
                    DraftSkill(
                        label="FastAPI",
                        aliases=[],
                        kind="tech",
                        source="Example Labs",
                        evidence="Built Python and FastAPI services on AWS",
                    )
                ]
            )
        # Kubernetes called Present, citing a skill that exists but is not Kubernetes.
        return Comparison(
            verdicts=[Verdict(label="Kubernetes", present=True, skillIds=["s1"])], risks=[]
        )

    monkeypatch.setattr(matching, "generate", generate)
    monkeypatch.setattr(inventory, "generate", generate)
    return asked


async def test_a_run_reports_what_the_pipeline_got_right_and_wrong(model: list[str]) -> None:
    report = await runner.evaluate(dataset.load(SAMPLE))

    assert model == ["BriefDraft", "DraftInventory", "Comparison"]
    assert report["failures"] == []
    scores = report["rates"]
    # Three found, all real; AWS, the fourth, was not extracted.
    assert scores["requirementPrecision"] == 1.0
    assert scores["requirementRecall"] == 0.75
    assert scores["detailAccuracy"] == 1.0
    # Python is in the profile verbatim, so code decided it. Of Kubernetes and
    # Terraform, both labelled missing, the model wrongly claimed Kubernetes.
    assert scores["wrongPresentRate"] == 0.5
    assert scores["verdictAccuracy"] == pytest.approx(0.6667, abs=1e-4)
    assert report["promptVersions"]["compare"] == matching.COMPARE_VERSION


async def test_a_posting_the_model_cannot_answer_is_reported_not_raised(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def broken(*args: Any, **kwargs: Any) -> None:
        raise runner.llm.GenerationError("would not produce a valid BriefDraft")

    monkeypatch.setattr(matching, "generate", broken)

    report = await runner.evaluate(dataset.load(SAMPLE))

    assert [failure["posting"] for failure in report["failures"]] == ["sample-platform-engineer"]
    assert report["rates"]["requirementRecall"] is None


# --- before and after -----------------------------------------------------------


def report(**values: float) -> dict[str, Any]:
    names = {"requirementRecall", "wrongPresentRate", "verdictAccuracy"}
    return {
        "postings": 20,
        "profiles": 3,
        "failures": [],
        "models": {"compare": "local/model"},
        "promptVersions": {"compare": 2},
        "rates": {name: value for name, value in values.items() if name in names},
        "usage": {name: value for name, value in values.items() if name not in names},
    }


def test_a_change_is_worse_in_the_direction_that_matters() -> None:
    before = report(requirementRecall=0.80, wrongPresentRate=0.05, promptTokensPerPosting=6000)
    after = report(requirementRecall=0.85, wrongPresentRate=0.09, promptTokensPerPosting=3900)

    rows = {row["measure"]: row for row in runner.compare_reports(before, after)}

    assert not rows["requirementRecall"]["worse"]  # up, and up is good
    assert rows["wrongPresentRate"]["worse"]  # up, and up is the harmful direction
    assert not rows["promptTokensPerPosting"]["worse"]  # down, and down is the point
    assert rows["promptTokensPerPosting"]["change"] == -2100
    assert "WORSE" in runner.render(after, before)


def test_a_measure_missing_from_either_side_is_not_called_worse() -> None:
    rows = runner.compare_reports(report(), report(wrongPresentRate=0.2))

    assert not any(row["worse"] for row in rows)
