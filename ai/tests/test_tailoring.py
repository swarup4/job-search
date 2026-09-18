"""P5-13 — the no-fabrication guardrail on the tailoring step.

Every test here is a way the pipeline could put something in the resume that the
user never approved. None of them is about whether the wording reads nicely.
"""

from __future__ import annotations

import pytest

from agents.tailoring import (
    Placement,
    PlacementPlan,
    SelectionGateNotPassed,
    _current_role,
    _selected_labels,
    apply,
    invented_words,
    review,
)

ROLE = {
    "title": "Senior Engineer",
    "company": "Trigent",
    "current": True,
    "bullets": [
        "Built the payments service and cut checkout latency by 30%",
        "Mentored four engineers through the migration",
    ],
}

GROUPS = [
    {"name": "Languages", "items": ["Python", "Go"]},
    {"name": "Cloud", "items": ["AWS", "Docker"]},
]


def plan(*placements: Placement) -> PlacementPlan:
    return PlacementPlan(placements=list(placements))


def skill(keyword: str, group: str) -> Placement:
    return Placement(keyword=keyword, kind="skill", group=group, bullet="", rewritten="")


def bullet(keyword: str, original: str, rewritten: str) -> Placement:
    return Placement(keyword=keyword, kind="bullet", group="", bullet=original, rewritten=rewritten)


# --- the selection gate ------------------------------------------------------


def test_tailoring_refuses_a_match_the_user_has_not_reviewed() -> None:
    match = {
        "review": {"state": "pending", "selectedKeys": []},
        "missing": [{"key": "k8s", "label": "Kubernetes"}],
    }
    with pytest.raises(SelectionGateNotPassed):
        _selected_labels(match)


def test_tailoring_refuses_a_skipped_match() -> None:
    match = {"review": {"state": "skipped", "selectedKeys": []}, "missing": []}
    with pytest.raises(SelectionGateNotPassed):
        _selected_labels(match)


def test_only_the_ticked_keywords_become_labels() -> None:
    match = {
        "review": {"state": "selected", "selectedKeys": ["kubernetes"]},
        "missing": [
            {"key": "kubernetes", "label": "Kubernetes"},
            {"key": "terraform", "label": "Terraform"},
        ],
    }
    assert _selected_labels(match) == ["Kubernetes"]


# --- a keyword nobody ticked never reaches the resume ------------------------


def test_a_keyword_the_user_did_not_select_is_dropped() -> None:
    accepted, declined = review(plan(skill("Terraform", "Cloud")), ["Kubernetes"], ROLE, GROUPS)

    assert accepted == []
    # Kubernetes is declined because nothing placed it; Terraform is absent entirely,
    # because it was never the user's to decline.
    assert [item.label for item in declined] == ["Kubernetes"]


# --- a rewrite may not smuggle in a new fact ---------------------------------


def test_a_rewrite_that_invents_a_metric_is_declined() -> None:
    accepted, declined = review(
        plan(
            bullet(
                "Kubernetes",
                "Built the payments service and cut checkout latency by 30%",
                "Built the payments service on Kubernetes and cut checkout latency by 60%",
            )
        ),
        ["Kubernetes"],
        ROLE,
        GROUPS,
    )

    assert accepted == []
    assert "60" in declined[0].reason


def test_a_rewrite_that_invents_an_employer_is_declined() -> None:
    accepted, declined = review(
        plan(
            bullet(
                "Kubernetes",
                "Mentored four engineers through the migration",
                "Mentored four engineers at Google through the Kubernetes migration",
            )
        ),
        ["Kubernetes"],
        ROLE,
        GROUPS,
    )

    assert accepted == []
    assert "google" in declined[0].reason


def test_a_rewrite_of_a_bullet_that_does_not_exist_is_declined() -> None:
    accepted, declined = review(
        plan(
            bullet(
                "Kubernetes", "Led the Kubernetes platform team", "Led the Kubernetes platform team"
            )
        ),
        ["Kubernetes"],
        ROLE,
        GROUPS,
    )

    assert accepted == []
    assert "not one of the current role's bullets" in declined[0].reason


def test_a_rewrite_that_omits_the_keyword_is_declined() -> None:
    accepted, declined = review(
        plan(
            bullet(
                "Kubernetes",
                "Mentored four engineers through the migration",
                "Mentored four engineers through the platform migration",
            )
        ),
        ["Kubernetes"],
        ROLE,
        GROUPS,
    )

    assert accepted == []
    assert "does not contain the keyword" in declined[0].reason


def test_a_minimal_rewrite_is_accepted() -> None:
    accepted, declined = review(
        plan(
            bullet(
                "Kubernetes",
                "Built the payments service and cut checkout latency by 30%",
                "Built the payments service on Kubernetes and cut checkout latency by 30%",
            )
        ),
        ["Kubernetes"],
        ROLE,
        GROUPS,
    )

    assert [item.keyword for item in accepted] == ["Kubernetes"]
    assert declined == []


def test_invented_words_allows_the_keyword_and_plain_connectives() -> None:
    assert (
        invented_words(
            "Built the payments service", "Built the payments service with Kubernetes", "Kubernetes"
        )
        == []
    )


def test_invented_words_reports_a_new_tool() -> None:
    assert invented_words(
        "Built the payments service", "Built the payments service with Terraform", "Kubernetes"
    ) == ["terraform"]


# --- skill placement ---------------------------------------------------------


def test_a_skill_group_that_does_not_exist_is_declined() -> None:
    accepted, declined = review(
        plan(skill("Kubernetes", "Orchestration")), ["Kubernetes"], ROLE, GROUPS
    )

    assert accepted == []
    assert "not one of the resume's skill groups" in declined[0].reason


def test_a_skill_placed_in_a_real_group_is_accepted() -> None:
    accepted, _ = review(plan(skill("Kubernetes", "Cloud")), ["Kubernetes"], ROLE, GROUPS)

    assert accepted[0].kind == "skill"
    assert accepted[0].group == "Cloud"


def test_one_keyword_is_placed_once() -> None:
    accepted, _ = review(
        plan(skill("Kubernetes", "Cloud"), skill("Kubernetes", "Languages")),
        ["Kubernetes"],
        ROLE,
        GROUPS,
    )

    assert len(accepted) == 1


# --- what reaches the .tex ---------------------------------------------------

GRID_TEX = r"""\begin{tabularx}{\linewidth}{XXXX}
Python, Go \\
AWS, Docker \\
\end{tabularx}
\begin{itemize}
  \item Built the payments service and cut checkout latency by 30\%
  \item Mentored four engineers through the migration
\end{itemize}
"""

PILLS_TEX = r"""\skilltag{Python}\ \skilltag{Go}
\skilltag{AWS}\ \skilltag{Docker}
"""


def test_a_skill_lands_next_to_its_group_in_a_grid_template() -> None:
    tex, changes = apply(GRID_TEX, [skill("Kubernetes", "Cloud")], GROUPS)

    assert r"AWS, Docker, Kubernetes \\" in tex
    assert changes[0]["previous"] == r"AWS, Docker \\"


def test_a_skill_lands_as_a_pill_in_a_pill_template() -> None:
    tex, _ = apply(PILLS_TEX, [skill("Kubernetes", "Cloud")], GROUPS)

    assert r"\skilltag{Docker}\ \skilltag{Kubernetes}" in tex


def test_a_rewritten_bullet_replaces_the_line_it_came_from() -> None:
    placement = bullet(
        "Kubernetes",
        "Built the payments service and cut checkout latency by 30%",
        "Built the payments service on Kubernetes and cut checkout latency by 30%",
    )
    tex, changes = apply(GRID_TEX, [placement], GROUPS)

    assert r"\item Built the payments service on Kubernetes and cut checkout latency by 30\%" in tex
    assert "Built the payments service and cut" not in tex
    assert changes[0]["lineNo"] == 6


def test_a_placement_whose_line_is_not_in_the_tex_is_dropped() -> None:
    placement = bullet(
        "Kubernetes",
        "A bullet the stored resume does not contain",
        "A bullet the stored resume does not contain, on Kubernetes",
    )
    tex, changes = apply(GRID_TEX, [placement], GROUPS)

    assert tex == GRID_TEX
    assert changes == []


# --- which role is in play ---------------------------------------------------


def test_the_current_role_is_the_one_tailored() -> None:
    profile = {
        "work": [
            {"title": "Old", "start": "2015", "current": False},
            {"title": "Now", "start": "2021", "current": True},
        ]
    }
    assert _current_role(profile)["title"] == "Now"


def test_without_a_current_flag_the_latest_role_is_used() -> None:
    profile = {
        "work": [
            {"title": "Old", "start": "2015", "current": False},
            {"title": "Latest", "start": "2021", "current": False},
        ]
    }
    assert _current_role(profile)["title"] == "Latest"


def test_two_keywords_on_one_line_are_recorded_as_a_single_change() -> None:
    tex, changes = apply(
        PILLS_TEX, [skill("Kubernetes", "Cloud"), skill("Terraform", "Cloud")], GROUPS
    )

    assert len(changes) == 1
    assert changes[0]["previous"] == r"\skilltag{AWS}\ \skilltag{Docker}"
    assert changes[0]["text"].endswith(r"\skilltag{Kubernetes}\ \skilltag{Terraform}")
    assert changes[0]["text"] in tex
