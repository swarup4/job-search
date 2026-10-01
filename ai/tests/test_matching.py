"""P5-13 — what the match step is allowed to claim.

The brief may not show the user a quote the job description never contained, and
the comparison may not mark a requirement Present on evidence the profile does not
hold. The second is the one that matters: a wrong Present silently withholds a
keyword the user would otherwise have been offered.
"""

from __future__ import annotations

from typing import Any

import pytest

from agents import matching
from agents.inventory import Inventory, Skill
from agents.matching import (
    Brief,
    BriefDraft,
    Comparison,
    ExtractedKeyword,
    Requirement,
    RiskFinding,
    Verdict,
    coverage_score,
    profile_corpus,
    slug,
)
from rag import Span

JD = (
    "We are hiring a senior platform engineer. You will run our Kubernetes clusters and "
    "write Terraform for the AWS estate. Kubernetes experience is essential. "
    "You bring 6+ years of experience. Hybrid, three days a week in Pune."
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

INVENTORY = Inventory(
    profileHash="h",
    modelName="test",
    skills=[
        Skill(
            id="s1",
            label="Deployment pipeline",
            aliases=["CI/CD"],
            kind="practice",
            evidence="Ran the AWS estate and the deployment pipeline",
        ),
        Skill(id="s2", label="Docker", kind="tech", evidence="AWS, Docker"),
    ],
)

JOB = {"id": "j1", "title": "Platform Engineer", "company": "Acme", "location": "Pune"}


def req(label: str, mentions: int = 1) -> Requirement:
    return Requirement(kind="tech", key=slug(label), label=label, mentions=mentions, evidence="x")


def draft(*keywords: ExtractedKeyword, **constraints: Any) -> BriefDraft:
    fields = {"seniority": None, "minYears": None, "locationRule": None, "workMode": None}
    return BriefDraft(requirements=list(keywords), **{**fields, **constraints})


def answers(*replies: object, prompts: list[str] | None = None):
    """Stand in for the model, one reply per call, in order — recording each prompt."""
    queue = list(replies)

    async def fake(shape, prompt, *, system, max_tokens=2048, endpoint=None):
        if prompts is not None:
            prompts.append(prompt)
        return queue.pop(0)

    return fake


def refuse(*args: Any, **kwargs: Any) -> None:
    raise AssertionError("the model was called")


# --- the brief: a quote the JD does not contain is not shown to the user ------


async def test_a_requirement_with_an_invented_quote_is_dropped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        matching,
        "generate",
        answers(
            draft(
                ExtractedKeyword(
                    kind="tech", label="Kubernetes", evidence="run our Kubernetes clusters"
                ),
                ExtractedKeyword(
                    kind="tech",
                    label="Kafka",
                    evidence="You will operate our Kafka event streams daily",
                ),
            )
        ),
    )

    brief = await matching.build_brief(JD)

    assert [item.label for item in brief.requirements] == ["Kubernetes"]


async def test_mentions_are_counted_from_the_jd_not_taken_from_the_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        matching,
        "generate",
        answers(
            draft(
                ExtractedKeyword(
                    kind="tech", label="Kubernetes", evidence="run our Kubernetes clusters"
                )
            )
        ),
    )

    brief = await matching.build_brief(JD)

    assert brief.requirements[0].mentions == 2


async def test_the_same_requirement_is_offered_once(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        matching,
        "generate",
        answers(
            draft(
                ExtractedKeyword(
                    kind="tech", label="Kubernetes", evidence="run our Kubernetes clusters"
                ),
                ExtractedKeyword(
                    kind="tech", label="kubernetes", evidence="Kubernetes experience is essential."
                ),
            )
        ),
    )

    assert len((await matching.build_brief(JD)).requirements) == 1


async def test_stated_constraints_are_kept(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        matching,
        "generate",
        answers(
            draft(
                seniority="senior",
                minYears=6,
                locationRule="three days a week in Pune",
                workMode="hybrid",
            )
        ),
    )

    brief = await matching.build_brief(JD)

    assert (brief.seniority, brief.minYears, brief.workMode) == ("senior", 6, "hybrid")
    assert brief.locationRule == "three days a week in Pune"


async def test_a_constraint_the_jd_does_not_state_is_dropped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Each would become a risk flag the user acts on — a guessed one is a false alarm."""
    monkeypatch.setattr(
        matching,
        "generate",
        answers(
            draft(
                seniority="Staff", minYears=10, locationRule="Relocate to Berlin", workMode="remote"
            )
        ),
    )

    brief = await matching.build_brief(JD)

    assert (brief.seniority, brief.minYears, brief.locationRule, brief.workMode) == (
        None,
        None,
        None,
        None,
    )


async def test_the_jd_reaches_the_model_fenced(monkeypatch: pytest.MonkeyPatch) -> None:
    prompts: list[str] = []
    monkeypatch.setattr(matching, "generate", answers(draft(), prompts=prompts))

    await matching.build_brief(JD)

    assert prompts[0].startswith('<document name="job_description">')


# --- the brief is read once and stored ---------------------------------------


class Store:
    def __init__(self) -> None:
        self.briefs: list[tuple[str, dict[str, Any]]] = []

    async def store_brief(self, description_id: str, brief: dict[str, Any]) -> dict[str, Any]:
        self.briefs.append((description_id, brief))
        return {}


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch) -> Store:
    fake = Store()
    monkeypatch.setattr(matching.jobpilot_api, "store_brief", fake.store_brief)
    return fake


async def test_a_current_stored_brief_is_reused_without_the_model(
    monkeypatch: pytest.MonkeyPatch, store: Store
) -> None:
    monkeypatch.setattr(matching, "generate", refuse)
    stored = {
        "requirements": [req("Kubernetes").model_dump()],
        "workMode": "hybrid",
        "briefVersion": matching.BRIEF_VERSION,
    }

    brief = await matching.ensure_brief({"id": "d1", "jdText": JD, "brief": stored}, JOB)

    assert [item.label for item in brief.requirements] == ["Kubernetes"]
    assert store.briefs == []


async def test_a_brief_from_an_older_prompt_is_read_again_and_stored(
    monkeypatch: pytest.MonkeyPatch, store: Store
) -> None:
    monkeypatch.setattr(
        matching,
        "generate",
        answers(
            draft(
                ExtractedKeyword(
                    kind="tech", label="Terraform", evidence="write Terraform for the AWS estate"
                )
            )
        ),
    )
    stale = {"requirements": [], "briefVersion": matching.BRIEF_VERSION - 1}

    await matching.ensure_brief({"id": "d1", "jdText": JD, "brief": stale}, JOB)

    [(description_id, written)] = store.briefs
    assert description_id == "d1"
    assert [item["label"] for item in written["requirements"]] == ["Terraform"]
    assert written["briefVersion"] == matching.BRIEF_VERSION
    assert written["modelName"]


async def test_no_description_is_nothing_to_score(store: Store) -> None:
    with pytest.raises(matching.NoDescription):
        await matching.ensure_brief({"id": "d1", "jdText": "  "}, JOB)
    with pytest.raises(matching.NoDescription):
        await matching.ensure_brief(None, JOB)


# --- compare: which way it is allowed to be wrong -----------------------------


def comparison(*verdicts: Verdict, risks: list[RiskFinding] | None = None) -> Comparison:
    return Comparison(verdicts=list(verdicts), risks=risks or [])


async def run_compare(*requirements: Requirement) -> tuple[list[str], list[str], list[str]]:
    present, missing, risks = await matching.compare(
        Brief(requirements=list(requirements)), INVENTORY, PROFILE, JOB
    )
    return [i.label for i in present], [i.label for i in missing], [r.title for r in risks]


async def test_a_literal_profile_match_is_never_put_to_the_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompts: list[str] = []
    monkeypatch.setattr(matching, "generate", answers(comparison(), prompts=prompts))

    present, missing, _ = await run_compare(req("AWS"))

    assert (present, missing) == (["AWS"], [])
    assert "- AWS" not in prompts[0]


async def test_an_old_role_still_counts_as_evidence(monkeypatch: pytest.MonkeyPatch) -> None:
    """RASA sits in a role that ended in 2021. Reporting it Missing would invite the
    user to add what they already have."""
    monkeypatch.setattr(matching, "generate", answers(comparison()))

    present, _, _ = await run_compare(req("RASA"))

    assert present == ["RASA"]


async def test_an_inventory_alias_is_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(matching, "generate", answers(comparison()))

    present, _, _ = await run_compare(req("CI/CD"))

    assert present == ["CI/CD"]


async def test_a_verdict_citing_a_real_skill_is_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        matching,
        "generate",
        answers(comparison(Verdict(label="Release automation", present=True, skillIds=["s1"]))),
    )

    present, _, _ = await run_compare(req("Release automation"))

    assert present == ["Release automation"]


async def test_a_verdict_citing_an_invented_skill_falls_back_to_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        matching,
        "generate",
        answers(comparison(Verdict(label="Kubernetes", present=True, skillIds=["s99"]))),
    )

    present, missing, _ = await run_compare(req("Kubernetes", mentions=2))

    assert (present, missing) == ([], ["Kubernetes"])


async def test_a_present_verdict_citing_nothing_falls_back_to_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        matching,
        "generate",
        answers(comparison(Verdict(label="Kubernetes", present=True, skillIds=[]))),
    )

    _, missing, _ = await run_compare(req("Kubernetes"))

    assert missing == ["Kubernetes"]


async def test_a_verdict_for_a_requirement_nobody_asked_about_is_ignored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        matching,
        "generate",
        answers(comparison(Verdict(label="Rust", present=True, skillIds=["s2"]))),
    )

    present, missing, _ = await run_compare(req("Kubernetes"))

    assert (present, missing) == ([], ["Kubernetes"])


def risk(title: str, detail: str = "d", conflicts: bool = True) -> RiskFinding:
    return RiskFinding(category="seniority", title=title, detail=detail, conflicts=conflicts)


async def test_a_risk_is_reported_once(monkeypatch: pytest.MonkeyPatch) -> None:
    findings = [risk("Seniority gap", "Wants Staff; profile shows Senior.")]
    findings += [risk("seniority  gap", "again"), risk("Location conflict")]
    monkeypatch.setattr(matching, "generate", answers(comparison(risks=findings)))

    _, _, risks = await run_compare(req("AWS"))

    assert risks == ["Seniority gap", "Location conflict"]


async def test_at_most_five_risks_are_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    findings = [risk(f"Gap {n}") for n in range(6)]
    monkeypatch.setattr(matching, "generate", answers(comparison(risks=findings)))

    _, _, risks = await run_compare(req("AWS"))

    assert risks == [f"Gap {n}" for n in range(5)]


async def test_a_risk_the_candidate_meets_is_dropped(monkeypatch: pytest.MonkeyPatch) -> None:
    findings = [risk("Experience gap", "Wants 6 years; profile shows 8, which meets it.", False)]
    monkeypatch.setattr(matching, "generate", answers(comparison(risks=findings)))

    _, _, risks = await run_compare(req("AWS"))

    assert risks == []


async def test_a_skill_gap_dressed_as_a_risk_is_dropped(monkeypatch: pytest.MonkeyPatch) -> None:
    """The Missing list already shows it; a risk flag repeating it is noise."""
    findings = [
        risk("Missing core stack", "The job requires Kubernetes, which the profile lacks."),
        risk("Location conflict", "Requires Pune on site; candidate is in Bengaluru."),
    ]
    monkeypatch.setattr(matching, "generate", answers(comparison(risks=findings)))

    _, _, risks = await run_compare(req("Kubernetes"))

    assert risks == ["Location conflict"]


async def test_the_comparison_sees_the_inventory_not_the_whole_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompts: list[str] = []
    monkeypatch.setattr(matching, "generate", answers(comparison(), prompts=prompts))

    await run_compare(req("Kubernetes"))

    assert '<document name="skill_inventory">' in prompts[0]
    assert "s1: Deployment pipeline (also: CI/CD)" in prompts[0]
    assert "Built a RASA chatbot" not in prompts[0]


# --- the score ---------------------------------------------------------------


def test_the_score_weights_a_requirement_by_how_often_the_jd_asks_for_it() -> None:
    present = [Requirement(kind="tech", key="aws", label="AWS", mentions=1, evidence="x")]
    missing = [Requirement(kind="tech", key="k8s", label="Kubernetes", mentions=3, evidence="x")]

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


# --- P5-06: a near miss is a hint, never a verdict ---------------------------


def hint(text: str, score: float) -> Span:
    """What `nearest_spans` hands back: the closest indexed chunk and its cosine."""
    return Span(
        id="1", section="experience", text=text, source_ref="", score=score, scored_by="cosine"
    )


def requirement() -> Requirement:
    return Requirement(
        kind="tech",
        key="agentic-orchestration",
        label="agentic orchestration",
        mentions=1,
        evidence="Strong expertise in agentic orchestration",
    )


def index(monkeypatch, *spans: Span | None) -> list[list[str]]:
    """Stub the retrieval layer, recording the labels it was asked about."""
    asked: list[list[str]] = []

    async def fake(labels: list[str]) -> list[Span | None]:
        asked.append(labels)
        return list(spans)

    monkeypatch.setattr(matching, "nearest_spans", fake)
    return asked


async def test_near_miss_names_the_span_it_matched(monkeypatch) -> None:
    index(monkeypatch, hint("LangGraph pipelines", 0.52))

    result = await matching.flag_near_misses([requirement()])

    assert result[0].near_miss == "LangGraph pipelines"


async def test_a_distant_span_is_not_a_near_miss(monkeypatch) -> None:
    """Below the threshold calibrated in `rag/embeddings.py` — related and unrelated
    spans separate there, and this is the wrong side of the line."""
    index(monkeypatch, hint("Built a RASA chatbot", 0.24))

    result = await matching.flag_near_misses([requirement()])

    assert result[0].near_miss is None


async def test_a_near_miss_leaves_the_requirement_missing(monkeypatch) -> None:
    """Promoting it on a cosine would hide a keyword the user never got to tick —
    the same failure the comparison refuses in the other direction."""
    index(monkeypatch, hint("LangGraph pipelines", 0.52))

    result = await matching.flag_near_misses([requirement()])

    assert [item.key for item in result] == ["agentic-orchestration"]
    assert result[0].near_miss is not None


async def test_an_empty_index_is_not_a_near_miss(monkeypatch) -> None:
    """A profile nobody has indexed yet returns no span at all, which is a hint that
    cannot be given rather than one that was refused."""
    index(monkeypatch, None)

    assert await matching.flag_near_misses([requirement()]) == [requirement()]


async def test_the_labels_are_what_the_index_is_asked_about(monkeypatch) -> None:
    """The label, not the evidence sentence: the threshold was calibrated on short
    requirement labels against profile spans."""
    asked = index(monkeypatch, hint("LangGraph pipelines", 0.52))

    await matching.flag_near_misses([requirement()])

    assert asked == [["agentic orchestration"]]


async def test_nothing_missing_asks_the_index_nothing(monkeypatch) -> None:
    asked = index(monkeypatch)

    assert await matching.flag_near_misses([]) == []
    assert asked == []
