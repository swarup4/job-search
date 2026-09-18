"""P5-13 — what the match step is allowed to claim.

Extraction may not show the user a quote the job description never contained, and
the diff may not mark a requirement Present on evidence the profile does not hold.
The second is the one that matters: a wrong Present silently withholds a keyword the
user would otherwise have been offered.
"""

from __future__ import annotations

import pytest

from agents import matching
from agents.matching import (
    Diff,
    ExtractedKeyword,
    Extraction,
    Requirement,
    Verdict,
    coverage_score,
    profile_corpus,
    slug,
)

JD = (
    "We are hiring a platform engineer. You will run our Kubernetes clusters and "
    "write Terraform for the AWS estate. Kubernetes experience is essential."
)

PROFILE = {
    "name": "A Candidate",
    "role": "Senior Engineer",
    "profile": {"headline": "Platform engineer", "summary": "Backend and platform work."},
    "work": [
        {
            "title": "Senior Engineer",
            "company": "Trigent",
            "start": "2021",
            "current": True,
            "bullets": ["Ran the AWS estate and the deployment pipeline"],
            "projects": [],
        },
        {
            "title": "Engineer",
            "company": "LTI",
            "start": "2017",
            "end": "2021",
            "current": False,
            "bullets": ["Built a RASA chatbot for internal support"],
            "projects": [],
        },
    ],
    "skill": [{"name": "Cloud", "items": ["AWS", "Docker"]}],
    "education": [],
    "certification": [],
}


def answers(*replies: object):
    """Stand in for the model, one reply per call, in order."""
    queue = list(replies)

    async def fake(shape, prompt, *, system, max_tokens=2048):
        return queue.pop(0)

    return fake


# --- P5-03: a quote the JD does not contain is not shown to the user ---------


async def test_a_requirement_with_an_invented_quote_is_dropped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        matching,
        "generate",
        answers(
            Extraction(
                keywords=[
                    ExtractedKeyword(label="Kubernetes", evidence="run our Kubernetes clusters"),
                    ExtractedKeyword(
                        label="Kafka", evidence="You will operate our Kafka event streams daily"
                    ),
                ]
            )
        ),
    )

    found = await matching.extract_requirements(JD)

    assert [item.label for item in found] == ["Kubernetes"]


async def test_mentions_are_counted_from_the_jd_not_taken_from_the_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        matching,
        "generate",
        answers(
            Extraction(
                keywords=[
                    ExtractedKeyword(label="Kubernetes", evidence="run our Kubernetes clusters")
                ]
            )
        ),
    )

    found = await matching.extract_requirements(JD)

    assert found[0].mentions == 2


async def test_the_same_requirement_is_offered_once(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        matching,
        "generate",
        answers(
            Extraction(
                keywords=[
                    ExtractedKeyword(label="Kubernetes", evidence="run our Kubernetes clusters"),
                    ExtractedKeyword(
                        label="kubernetes", evidence="Kubernetes experience is essential."
                    ),
                ]
            )
        ),
    )

    assert len(await matching.extract_requirements(JD)) == 1


# --- P5-04: the diff, and which way it is allowed to be wrong ---------------


async def test_a_literal_profile_match_is_present_without_asking_the_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def refuse(*args, **kwargs):
        raise AssertionError("the model was asked about a requirement the profile states verbatim")

    monkeypatch.setattr(matching, "generate", refuse)

    present, missing = await matching.split_by_profile(
        [Requirement(key="aws", label="AWS", mentions=1, evidence="the AWS estate")], PROFILE
    )

    assert [item.label for item in present] == ["AWS"]
    assert missing == []


async def test_an_old_role_still_counts_as_evidence(monkeypatch: pytest.MonkeyPatch) -> None:
    """RASA sits in a role that ended in 2021. Reporting it Missing would invite the
    user to add what they already have."""

    def refuse(*args, **kwargs):
        raise AssertionError("the model was asked about a skill the profile already names")

    monkeypatch.setattr(matching, "generate", refuse)

    present, _ = await matching.split_by_profile(
        [Requirement(key="rasa", label="RASA", mentions=1, evidence="RASA is required")], PROFILE
    )

    assert [item.label for item in present] == ["RASA"]


async def test_an_unverifiable_present_verdict_falls_back_to_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        matching,
        "generate",
        answers(
            Diff(
                verdicts=[
                    Verdict(
                        label="Kubernetes",
                        present=True,
                        evidence="Operated Kubernetes clusters in production",
                    )
                ]
            )
        ),
    )

    present, missing = await matching.split_by_profile(
        [
            Requirement(
                key="kubernetes",
                label="Kubernetes",
                mentions=2,
                evidence="run our Kubernetes clusters",
            )
        ],
        PROFILE,
    )

    assert present == []
    assert [item.label for item in missing] == ["Kubernetes"]


async def test_a_present_verdict_quoting_the_profile_is_kept(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        matching,
        "generate",
        answers(
            Diff(
                verdicts=[
                    Verdict(
                        label="Deployment pipelines",
                        present=True,
                        evidence="Ran the AWS estate and the deployment pipeline",
                    )
                ]
            )
        ),
    )

    present, _ = await matching.split_by_profile(
        [
            Requirement(
                key="deployment-pipelines",
                label="Deployment pipelines",
                mentions=1,
                evidence="You will run our deployment pipelines",
            )
        ],
        PROFILE,
    )

    assert [item.label for item in present] == ["Deployment pipelines"]


# --- the score ---------------------------------------------------------------


def test_the_score_weights_a_requirement_by_how_often_the_jd_asks_for_it() -> None:
    present = [Requirement(key="aws", label="AWS", mentions=1, evidence="x")]
    missing = [Requirement(key="k8s", label="Kubernetes", mentions=3, evidence="x")]

    assert coverage_score(present, missing) == 25


def test_a_job_with_no_extractable_requirements_scores_zero() -> None:
    assert coverage_score([], []) == 0


# --- odds and ends -----------------------------------------------------------


def test_the_corpus_carries_every_role_not_just_the_current_one() -> None:
    corpus = profile_corpus(PROFILE)

    assert "RASA" in corpus
    assert "Ran the AWS estate" in corpus


def test_slugs_are_stable_across_spelling() -> None:
    assert slug("CI/CD") == slug("ci cd") == "ci-cd"
