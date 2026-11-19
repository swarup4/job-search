"""P10-09 — the budget table in 05-Roadmap-Backlog.md (Phase 14), as tests.

One test per prompt builds the largest input that prompt can realistically be handed
and fails if any row of the table is exceeded:

| part                              | limit (tokens)            |
|-----------------------------------|---------------------------|
| system prompt                     | 15% of the window         |
| all input                         | 60% of the window         |
| reserved for a retry              | `llm.REPAIR_TOKENS`       |
| candidate block                   | `llm.CANDIDATE_TOKENS`    |
| posting text, after cleaning      | `llm.POSTING_TOKENS`      |
| tool definitions in any call      | `llm.TOOL_DEFINITION_TOKENS` |
| one tool result                   | `llm.TOOL_RESULT_TOKENS`  |

"Largest realistic" means built through the same code a real call goes through — the
cleaner, the candidate block, the prompt builders — from inputs far past any cap, so a
change that lets a part grow fails here rather than as a truncated prompt in a run.
No call carries tools yet; the last two rows are pinned so step 6 inherits them.
"""

from __future__ import annotations

from typing import Any

import pytest

from agents import inventory, matching, parsing, tailoring
from agents.cleaning import clean_posting
from agents.inventory import INVENTORY_SYSTEM, MAX_OUTPUT_TOKENS, Inventory, Skill
from agents.matching import BRIEF_SYSTEM, COMPARE_SYSTEM, Brief, Requirement
from agents.parsing import PARSE_SYSTEM
from agents.tailoring import TAILOR_SYSTEM
from config import llm

WINDOW = llm.LLM_NUM_CTX

# The longest reply each call may ask for: `generate`'s default, or the call's own.
REPLY = {"parse": 2_048, "brief": 2_048, "compare": 2_048, "tailor": 2_048}

SYSTEMS = {
    "parse": PARSE_SYSTEM,
    "brief": BRIEF_SYSTEM,
    "compare": COMPARE_SYSTEM,
    "inventory": INVENTORY_SYSTEM,
    "tailor": TAILOR_SYSTEM,
}


def huge_posting() -> str:
    """A captured career page at its worst: navigation, a long posting, and far more
    benefits and legal text than posting. About 60,000 characters."""
    nav = "\n".join(
        f"[Careers section number {n}](https://careers.example.com/section/{n}?utm=abc)"
        for n in range(200)
    )
    duties = "## Responsibilities\n" + "\n".join(
        f"- Duty {n}: design, build and operate distributed services on Kubernetes and AWS"
        for n in range(30)
    )
    needs = "## Requirements\n" + "\n".join(
        f"- Requirement {n}: {n + 3}+ years with Python, Terraform, PostgreSQL and Kafka"
        for n in range(30)
    )
    perks = "## Benefits\n" + "\n".join(
        f"- Perk {n}: health cover, a learning budget, and flexible working hours"
        for n in range(300)
    )
    legal = "## Equal Opportunity\n" + "\n".join(
        f"Clause {n}: we are an equal opportunity employer and value diversity." for n in range(300)
    )
    sections = ["# Staff Platform Engineer", nav, duties, needs, perks, legal]
    return "\n\n".join(sections)


def huge_profile() -> dict[str, Any]:
    """Twenty years, ten roles, every bullet long."""
    return {
        "name": "A Candidate",
        "role": "Principal Engineer",
        "profile": {"headline": "Platform and AI engineering leader " * 4, "location": "Bengaluru"},
        "work": [
            {
                "title": f"Senior Engineer {n}",
                "company": f"Company number {n} Private Limited",
                "start": str(2005 + n * 2),
                "end": str(2007 + n * 2),
                "current": n == 9,
                "bullets": [f"Delivered project {n}-{b} " + "at scale " * 20 for b in range(8)],
                "projects": [],
            }
            for n in range(10)
        ],
        "skill": [
            {"name": f"Group {g}", "items": [f"Skill {g}-{i}" for i in range(20)]}
            for g in range(10)
        ],
        "education": [{"degree": "B.Tech Computer Science", "institution": "An Institute"}] * 3,
        "certification": [],
    }


def huge_inventory() -> Inventory:
    """The most skills an inventory can hold, each with the longest quote stored."""
    return Inventory(
        profileHash="h",
        modelName="m",
        skills=[
            Skill(
                id=f"s{n}",
                label=f"Skill number {n} with a long name",
                aliases=["first alias", "second alias", "third alias"],
                kind="tech",
                evidence="evidence of using this skill in production " * 20,
            )
            for n in range(1, inventory.MAX_SKILLS + 1)
        ],
    )


def tokens(text: str) -> int:
    return llm.estimate_tokens(text)


def fits(name: str, endpoint: llm.Endpoint, prompt: str, reply: int) -> None:
    """Rows one to three of the table, for one prompt."""
    system = SYSTEMS[name]
    assert tokens(system) <= int(WINDOW * llm.SYSTEM_BUDGET), f"{name}: system prompt"
    assert tokens(system) + tokens(prompt) <= int(WINDOW * llm.INPUT_BUDGET), f"{name}: input"
    assert tokens(system) + tokens(prompt) + llm.REPAIR_TOKENS + reply <= WINDOW, f"{name}: retry"
    # And the check every real call makes agrees.
    llm.check_budget(endpoint, system, prompt, reply)


# --- the parts ----------------------------------------------------------------


def test_a_posting_never_takes_more_than_its_share() -> None:
    posting = huge_posting()
    assert tokens(posting) > 4 * llm.POSTING_TOKENS

    cleaned = clean_posting(posting)

    assert tokens(cleaned.text) <= llm.POSTING_TOKENS
    # Cut down by dropping what scoring does not need, not by losing the posting.
    # The title stays, the menu under it is shortened, and the requirements at the
    # far end of the page are all still there.
    assert cleaned.text.startswith("# Staff Platform Engineer")
    assert "Requirement 29" in cleaned.text and "Duty 29" in cleaned.text
    assert "Perk" not in cleaned.text and "Clause" not in cleaned.text


def test_the_candidate_block_never_takes_more_than_its_share() -> None:
    block = inventory.render_candidate(huge_inventory().skills, huge_profile())

    assert tokens(block) <= llm.CANDIDATE_TOKENS
    assert f"s{inventory.MAX_SKILLS}:" in block


# --- one test per prompt ------------------------------------------------------


def test_the_brief_prompt_fits_at_its_largest() -> None:
    posting = clean_posting(huge_posting(), matching.MAX_JD_CHARS)
    fits("brief", llm.BRIEF, llm.as_document("job_description", posting.text), REPLY["brief"])


def test_the_parse_prompt_fits_at_its_largest() -> None:
    page = clean_posting(huge_posting(), parsing.MAX_PAGE_CHARS)
    fits("parse", llm.DEFAULT, llm.as_document("career_page", page.text), REPLY["parse"])


def test_the_compare_prompt_fits_at_its_largest() -> None:
    """The most a brief can hold against the most an inventory can hold."""
    requirements = [
        Requirement(
            key=f"r{n}",
            label=f"Requirement label number {n} at full length"[:60],
            kind="tech",
            mentions=1,
            evidence="x",
        )
        for n in range(25)
    ]
    brief = Brief(
        requirements=requirements,
        seniority="Principal",
        minYears=15,
        locationRule="L" * 200,
        workMode="hybrid",
    )
    job = {"title": "T" * 200, "company": "C" * 120, "location": "P" * 200}
    stored = huge_inventory()
    stored.candidateBlock = inventory.render_candidate(stored.skills, huge_profile())

    prompt = matching._comparison_prompt(requirements, stored, brief, job, huge_profile())

    fits("compare", llm.MATCH, prompt, REPLY["compare"])


def test_the_inventory_prompt_fits_beside_its_long_reply() -> None:
    """The one call with a long reply. A 12,000-character profile is a twenty-year
    career written out in full; past that `check_budget` refuses, and says so."""
    prompt = llm.as_document("profile", "x" * 12_000)
    fits("inventory", llm.INVENTORY, prompt, MAX_OUTPUT_TOKENS)

    with pytest.raises(llm.BudgetExceeded):
        llm.check_budget(
            llm.INVENTORY,
            INVENTORY_SYSTEM,
            llm.as_document("profile", "x" * 40_000),
            MAX_OUTPUT_TOKENS,
        )


def test_the_tailoring_prompt_fits_at_its_largest() -> None:
    """A long current role, every skill group full, and every keyword a match can offer."""
    role = {
        "title": "Principal Engineer",
        "company": "A Company Private Limited",
        "bullets": [f"Bullet {n}: " + "delivered at scale " * 15 for n in range(15)],
    }
    groups = [
        {"name": f"Group {g}", "items": [f"Skill {g}-{i}" for i in range(20)]} for g in range(10)
    ]
    keywords = [f"Keyword number {n} at full length"[:60] for n in range(25)]

    fits("tailor", llm.DEFAULT, tailoring.placement_prompt(keywords, role, groups), REPLY["tailor"])


# --- the rows no call uses yet ------------------------------------------------


def test_the_tool_budgets_are_pinned_for_the_graph_step() -> None:
    """No call carries tools today. When one does (docs/12, step 6), these are the
    limits its test is written against: a tenth of the window for every definition
    in a call, and a result that is paged past a thousand tokens."""
    assert llm.TOOL_DEFINITION_TOKENS == 1_600 <= int(WINDOW * 0.10)
    assert llm.TOOL_RESULT_TOKENS == 1_000


def test_the_parts_add_up_inside_the_input_budget() -> None:
    """Candidate, posting and the largest system prompt together must leave the input
    budget room for the question, or no prompt that needs all three could be built."""
    largest_system = max(tokens(system) for system in SYSTEMS.values())
    used = llm.CANDIDATE_TOKENS + llm.POSTING_TOKENS + largest_system

    assert used < int(WINDOW * llm.INPUT_BUDGET)
