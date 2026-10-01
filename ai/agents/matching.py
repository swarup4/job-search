"""The JD match/score capability: brief, compare, flag, score, persist.

Phase 5 calls these functions directly — there is no graph yet, deliberately, so a
wrong answer stays debuggable. Phase 8 wraps `rectify` in a LangGraph node; the file
is named for the capability so that step is a wrapping rather than a move.

Two things are read once and stored, so a score costs one model call:

| read      | from               | stored on                | rebuilt when                     |
|-----------|--------------------|--------------------------|----------------------------------|
| brief     | the posting        | its job description      | `BRIEF_VERSION` changes          |
| inventory | the whole profile  | the account (see inventory.py) | the profile or its model changes |

What each step is allowed to see is a guardrail, not only an economy:

| step        | sees                                              |
|-------------|---------------------------------------------------|
| brief       | the JD, fenced as untrusted                       |
| compare     | the brief's requirements, the inventory, a digest |
| near misses | the indexed profile chunks, via Voyage            |

Nothing reaches Present unless it traces to the profile: a literal match against the
profile text, an inventory label or alias, or a verdict citing an inventory id — and
every inventory entry's quote was checked against the profile when it was built.
"""

from __future__ import annotations

import asyncio
import re
import sys
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

from agents.evidence import (
    flatten,
    occurrences,
    profile_corpus,
    profile_digest,
    sentence_with,
    slug,
    verified_span,
)
from agents.inventory import KIND_RULE, Inventory, ensure_inventory
from config.llm import BRIEF, MATCH, UNTRUSTED_RULE, as_document, generate
from mcp_servers import jobpilot_api
from rag import NEAR_MISS_THRESHOLD, embed_pending, nearest_spans

# An unbounded prompt is a cost problem on a hosted model and a context problem on a
# local one. A JD longer than this is padding — boilerplate, benefits, legal text.
MAX_JD_CHARS = 12_000

# Bumped when BRIEF_SYSTEM or the brief's shape changes, so stored briefs are re-read.
BRIEF_VERSION = 1

# The inventory listing is the bulk of a comparison prompt. A shortened quote is
# enough for the model to tell skills apart; the full quote stays in the store.
LISTED_EVIDENCE_CHARS = 100

Kind = Literal["tech", "qualification", "practice"]
WorkMode = Literal["on_site", "hybrid", "remote"]

# Words that have to appear in the posting before a work mode is believed.
MODE_WORDS = {
    "remote": r"\bremote\b|work from home|\bwfh\b",
    "hybrid": r"\bhybrid\b",
    "on_site": r"\bon[- ]?site\b|\bin[- ]office\b|work from office|\bwfo\b",
}


# Length caps on everything the model writes. Ollama compiles the schema into a
# grammar, so a cap is enforced while generating: without them the model rambled
# inside a `detail` string until the reply hit max_tokens, failed validation, and was
# retried — minutes per job for an answer it was never going to finish.
SHORT = 80
QUOTE = 400


class ExtractedKeyword(BaseModel):
    label: str = Field(max_length=SHORT)
    kind: Kind
    evidence: str = Field(max_length=QUOTE)


class BriefDraft(BaseModel):
    requirements: list[ExtractedKeyword] = Field(max_length=25)
    seniority: str | None = Field(max_length=40)
    minYears: int | None
    locationRule: str | None = Field(max_length=200)
    workMode: WorkMode | None


class Requirement(BaseModel):
    """One requirement, after the JD has been checked for it."""

    key: str
    label: str
    kind: Kind
    mentions: int
    evidence: str
    # A profile span that reads like this requirement under different wording. Set on
    # Missing requirements only, and never acted on without the user.
    near_miss: str | None = None


class Brief(BaseModel):
    """A posting as scoring needs it. Every field was checked against the JD."""

    requirements: list[Requirement]
    seniority: str | None = None
    minYears: int | None = None
    locationRule: str | None = None
    workMode: WorkMode | None = None


class Verdict(BaseModel):
    label: str = Field(max_length=SHORT)
    present: bool
    # Inventory ids, not quotes: an id either exists or it does not, where a quote
    # had to be searched for and the model kept stitching fragments together.
    skillIds: list[Annotated[str, Field(max_length=8)]] = Field(max_length=5)


class RiskFinding(BaseModel):
    # No category for a missing skill: told in words not to report one, a small model
    # did anyway, repeating the Missing list as risks. A closed enum cannot.
    category: Literal["seniority", "experience", "credential", "domain", "location", "work_mode"]
    title: str = Field(max_length=SHORT)
    detail: str = Field(max_length=300)
    # Asked so the model checks itself: findings it admits the candidate meets were
    # coming back as "Seniority mismatch … which matches".
    conflicts: bool


class Comparison(BaseModel):
    verdicts: list[Verdict] = Field(max_length=30)
    risks: list[RiskFinding] = Field(max_length=6)


class Risk(BaseModel):
    key: str
    title: str
    detail: str


BRIEF_SYSTEM = f"""You read one job description and report what it requires.

{UNTRUSTED_RULE}

`requirements` — the concrete, checkable requirements it states: technologies, tools, platforms, languages, frameworks, methodologies, certifications and qualifications. Exclude generic traits ("team player", "excellent communication") and anything about the company itself.
- `label` uses the description's own wording, at most four words.
- {KIND_RULE}
- `evidence` is a span copied VERBATIM from the description containing the requirement. Never paraphrase, never join spans.
- Never list a requirement the text does not state. At most 20, most important first.
- Years of experience and seniority are constraints, never requirements — report them only below.

Constraints — null unless the description states it outright:
- `seniority`: the level word it uses, e.g. "Senior", "Lead", "Staff".
- `minYears`: the minimum years of experience, as a number.
- `locationRule`: its location or relocation requirement, copied verbatim.
- `workMode`: on_site, hybrid or remote."""

COMPARE_SYSTEM = f"""You compare a job's requirements with a candidate's skill inventory, and flag mismatches a human should see before applying.

{UNTRUSTED_RULE}

Verdicts:
- Exactly one verdict per requirement, with the requirement's label unchanged.
- `present` is true only when an inventory skill is the same skill. A related skill is not the same skill.
- `skillIds` lists the inventory ids that show it, e.g. ["s3"]. Empty when `present` is false.

Risks — a constraint of the job the candidate does not meet:
- `category`: seniority, experience (years), credential (a required degree or certification), domain, location or work_mode.
- `conflicts` is true only when the candidate does NOT meet it. If they meet it, leave it out.
- `title` is at most six words. `detail` is one sentence naming the job's requirement and what the profile shows instead.
- Report nothing you cannot ground in both documents. An empty list is right for a well-matched job. At most 5."""


class NoDescription(RuntimeError):
    """Nothing to score: no job description is stored for this job."""


async def score_job(job_id: str) -> dict[str, Any]:
    """Score one job from scratch — the scoring run's entry point."""
    return await rectify(job_id)


async def rectify(job_id: str, brief: Brief | None = None) -> dict[str, Any]:
    """Score one job against the profile and persist the result through `server`.

    `brief` is the posting's, when the caller has already read it — analysis does, to
    store the tech stack — so one run pays for reading the posting once.

    The match lands with its review gate PENDING. Nothing here selects a keyword —
    that is the user's answer at the interrupt, and the server refuses a resume
    built on keywords they did not tick. (FR-2.5, FR-7.3)
    """
    job = await jobpilot_api.get_job(job_id)
    description = await jobpilot_api.get_description_for_job(job_id)
    profile = await jobpilot_api.get_profile()

    if brief is None:
        brief = await ensure_brief(description, job)
    inventory = await ensure_inventory(profile)
    present, missing, risks = await compare(brief, inventory, profile, job)
    # Chunks the user edited since the last run have no vector yet, so the near-miss
    # check would quietly come back empty. One GET when there is nothing to do.
    await embed_pending()
    missing = await flag_near_misses(missing)

    payload = {
        "jobId": job_id,
        "score": coverage_score(present, missing),
        "present": [{"label": item.label} for item in present],
        "missing": [
            {
                "key": item.key,
                "label": item.label,
                "mentions": item.mentions,
                "evidence": item.evidence,
                "nearMiss": item.near_miss,
            }
            for item in missing
        ],
        "risks": [{"key": item.key, "title": item.title, "detail": item.detail} for item in risks],
        "modelName": MATCH.provenance,
    }
    return await jobpilot_api.write_match(payload)


# --- the brief: the posting, read once ---------------------------------------


async def ensure_brief(description: dict[str, Any] | None, job: dict[str, Any]) -> Brief:
    """The stored brief if it is current, else a fresh one, stored for next time."""
    text = _jd_text(description, job.get("techStack"))
    if not description or not text.strip():
        raise NoDescription("no job description is stored for this job")

    stored = description.get("brief")
    if stored and stored.get("briefVersion") == BRIEF_VERSION:
        return Brief.model_validate(stored)

    brief = await build_brief(text)
    await jobpilot_api.store_brief(
        description["id"],
        {**brief.model_dump(), "modelName": BRIEF.provenance, "briefVersion": BRIEF_VERSION},
    )
    return brief


async def build_brief(jd_text: str) -> Brief:
    """Read a JD into requirements and constraints, keeping only what it backs up."""
    draft = await generate(
        BriefDraft, as_document("job_description", jd_text), system=BRIEF_SYSTEM, endpoint=BRIEF
    )

    haystack = flatten(jd_text)
    requirements: list[Requirement] = []
    seen: set[str] = set()
    for keyword in draft.requirements:
        label = keyword.label.strip()
        if not label or len(label) > 60:
            continue

        # A quote nobody can find in the JD is the screen showing the user something
        # the posting never said, so the requirement is dropped rather than shown
        # with an invented one.
        evidence = verified_span(keyword.evidence, haystack) or sentence_with(label, jd_text)
        if evidence is None:
            continue

        key = slug(label)
        if not key or key in seen:
            continue
        seen.add(key)
        requirements.append(
            Requirement(
                key=key,
                label=label,
                kind=keyword.kind,
                # Counted here rather than taken from the model: how often a word
                # appears is arithmetic, and the screen ranks by it.
                mentions=max(1, occurrences(label, haystack)),
                evidence=evidence,
            )
        )

    # A constraint feeds a risk flag the user acts on, so one the JD does not state is
    # dropped rather than passed on as the model's guess.
    seniority = (draft.seniority or "").strip()
    location = verified_span(draft.locationRule or "", haystack)
    return Brief(
        requirements=requirements,
        seniority=seniority if seniority and occurrences(seniority, haystack) else None,
        minYears=draft.minYears if _states_years(draft.minYears, jd_text) else None,
        locationRule=location[:200] if location else None,
        workMode=draft.workMode if _states_mode(draft.workMode, jd_text) else None,
    )


def _states_years(years: int | None, text: str) -> bool:
    if years is None or not 0 <= years <= 50:
        return False
    pattern = rf"(?<!\d){years}(?!\d)[^.\n]{{0,25}}\b(?:years?|yrs?)\b"
    return re.search(pattern, text, re.IGNORECASE) is not None


def _states_mode(mode: str | None, text: str) -> bool:
    return mode is not None and re.search(MODE_WORDS[mode], text, re.IGNORECASE) is not None


# --- compare: requirements against the inventory -----------------------------


async def compare(
    brief: Brief, inventory: Inventory, profile: dict[str, Any], job: dict[str, Any]
) -> tuple[list[Requirement], list[Requirement], list[Risk]]:
    """Present, Missing and the risk flags, in one model call."""
    flat_profile = flatten(profile_corpus(profile))
    names = {flatten(name) for skill in inventory.skills for name in (skill.label, *skill.aliases)}

    # A label sitting verbatim in the profile, or naming an inventory skill, is a fact
    # rather than a judgement, so it never reaches the model — and can never be
    # reported Missing by a bad one.
    literal = {
        item.key
        for item in brief.requirements
        if occurrences(item.label, flat_profile) or flatten(item.label) in names
    }
    undecided = [item for item in brief.requirements if item.key not in literal]

    # Asked even with nothing undecided: the risk flags come from the same call.
    comparison = await generate(
        Comparison,
        _comparison_prompt(undecided, inventory, brief, job, profile),
        system=COMPARE_SYSTEM,
        endpoint=MATCH,
    )

    known_ids = {skill.id for skill in inventory.skills}
    by_key = {item.key: item for item in undecided}
    claimed: set[str] = set()
    for verdict in comparison.verdicts:
        key = slug(verdict.label)
        # An unsupported "already have it" is the dangerous direction: it hides a
        # keyword the user would otherwise have been offered. A verdict citing no real
        # inventory entry sends the requirement back to Missing, where they decide.
        if verdict.present and key in by_key and known_ids.intersection(verdict.skillIds):
            claimed.add(key)

    evidenced = literal | claimed
    present = [item for item in brief.requirements if item.key in evidenced]
    missing = [item for item in brief.requirements if item.key not in evidenced]
    return present, missing, _risks(comparison.risks, brief.requirements)


def _comparison_prompt(
    undecided: list[Requirement],
    inventory: Inventory,
    brief: Brief,
    job: dict[str, Any],
    profile: dict[str, Any],
) -> str:
    requirements = "\n".join(f"- {item.label}" for item in undecided) or "(none to judge)"
    skills = "\n".join(
        f"{skill.id}: {skill.label}"
        + (f" (also: {', '.join(skill.aliases)})" if skill.aliases else "")
        + f" — {skill.evidence[:LISTED_EVIDENCE_CHARS]}"
        for skill in inventory.skills
    )
    constraints = "\n".join(
        [
            f"Title: {job.get('title', '')} at {job.get('company', '')}",
            f"Location: {job.get('location', '')}",
            f"Seniority: {brief.seniority or 'not stated'}",
            f"Minimum years: {brief.minYears if brief.minYears is not None else 'not stated'}",
            f"Location rule: {brief.locationRule or 'not stated'}",
            f"Work mode: {brief.workMode or job.get('workMode') or 'not stated'}",
            "Requires: " + ", ".join(item.label for item in brief.requirements),
        ]
    )
    return (
        f"Requirements to judge:\n{requirements}\n\n"
        f"{as_document('skill_inventory', skills or '(empty)')}\n\n"
        f"{as_document('job', constraints)}\n\n"
        f"{as_document('candidate', profile_digest(profile))}"
    )


def _risks(findings: list[RiskFinding], requirements: list[Requirement]) -> list[Risk]:
    """Mismatches the user should see. Surfaced, never selectable — acting on one
    would be a misrepresentation. (FR-2.4)"""
    labels = [item.label for item in requirements]
    risks: list[Risk] = []
    seen: set[str] = set()
    for finding in findings:
        title, detail = finding.title.strip(), finding.detail.strip()
        key = slug(title)
        if not (finding.conflicts and title and detail) or key in seen:
            continue
        # A finding naming a requirement is a skill gap in disguise, and the user is
        # already shown that one as Missing.
        flat = flatten(f"{title} {detail}")
        if any(occurrences(label, flat) for label in labels):
            continue
        seen.add(key)
        risks.append(Risk(key=key, title=title, detail=detail))
        if len(risks) == 5:
            break
    return risks


# --- P5-06: near misses, locally embedded ------------------------------------


async def flag_near_misses(missing: list[Requirement]) -> list[Requirement]:
    """Mark a Missing requirement that the profile appears to state in other words.

    The comparison works on wording and on the inventory; a requirement the JD calls
    "agentic orchestration" and the profile calls "LangGraph multi-agent pipeline" can
    survive both and reach the user as Missing, which invites them to add what they
    already have.

    Since P6-04 the spans come from the stored chunks rather than being re-embedded
    for every job: the profile changes when the user edits it, not when a new posting
    turns up.

    The flag is advisory and nothing more. The requirement stays Missing and stays
    selectable: telling the user they may already have this is safe, deciding it for
    them is the fabrication the comparison exists to prevent.
    """
    if not missing:
        return missing

    spans = await nearest_spans([item.label for item in missing])
    for item, span in zip(missing, spans, strict=True):
        if span is not None and span.score >= NEAR_MISS_THRESHOLD:
            item.near_miss = span.text
    return missing


# --- the score ---------------------------------------------------------------


def coverage_score(present: list[Requirement], missing: list[Requirement]) -> int:
    """Keyword coverage, weighted by how often the JD asks for each requirement.

    This stays the score. P5-06 originally called for JD-embedding similarity, but a
    cosine between a JD and a resume lands in the same narrow band for every job in a
    field and cannot separate a good fit from an average one — and it cannot be
    explained to someone asking why a job scored 62. Arithmetic over verdicts the user
    can see on screen can. The embeddings went to `flag_near_misses` instead.
    """
    covered = sum(item.mentions for item in present)
    total = covered + sum(item.mentions for item in missing)
    return round(100 * covered / total) if total else 0


# --- JD text -----------------------------------------------------------------


def tech_stack(requirements: list[Requirement]) -> list[str]:
    """The technologies among a posting's requirements, in the order it ranks them."""
    return list(dict.fromkeys(item.label for item in requirements if item.kind == "tech"))


def _jd_text(description: dict[str, Any] | None, stack: list[str] | None = None) -> str:
    """The posting's prose, with its stored stack appended as a hint. Empty when the
    job has no description yet — nothing to score rather than an error."""
    if not description:
        return ""
    parts = [description.get("jdText", "")]
    if stack:
        parts.append("Tech stack named in the posting: " + ", ".join(stack))
    return "\n\n".join(part for part in parts if part)[:MAX_JD_CHARS]


if __name__ == "__main__":

    async def main() -> None:
        if len(sys.argv) < 3:
            print("usage: python -m agents.matching <jwt> <job_id>")
            return
        jobpilot_api.set_token(sys.argv[1])
        match = await rectify(sys.argv[2])
        print(f"score {match['score']} via {match['modelName']}")
        print("present:", [item["label"] for item in match["present"]])
        print("missing:", [item["label"] for item in match["missing"]])
        for item in match["missing"]:
            if item.get("nearMiss"):
                print(f"  near miss — {item['label']}: {item['nearMiss']}")
        print("risks:  ", [item["title"] for item in match["risks"]])

    asyncio.run(main())
