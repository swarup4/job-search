"""The JD match/score capability: extract, diff, flag, score, persist.

Phase 5 calls these functions directly — there is no graph yet, deliberately, so a
wrong answer stays debuggable. Phase 8 wraps `rectify` in a LangGraph node; the file
is named for the capability so that step is a wrapping rather than a move.

What each step is allowed to see is a guardrail, not only an economy:

| step            | sees                                  |
|-----------------|---------------------------------------|
| extraction      | the JD                                |
| diff            | the whole profile — every role         |
| risk flags      | the JD and a profile digest            |

The diff stays wide on purpose. A skill sitting in a role from six years ago is
still a skill the candidate has, and a diff that could not see it would report it
Missing and invite the user to add what they already have.
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel

from config.llm import generate
from config.settings import settings
from mcp_servers import jobpilot_api

# An unbounded prompt is a cost problem on a hosted model and a context problem on a
# local one. A JD longer than this is padding — boilerplate, benefits, legal text.
MAX_JD_CHARS = 12_000


class ExtractedKeyword(BaseModel):
    label: str
    evidence: str


class Extraction(BaseModel):
    keywords: list[ExtractedKeyword]


class Verdict(BaseModel):
    label: str
    present: bool
    evidence: str


class Diff(BaseModel):
    verdicts: list[Verdict]


class RiskFinding(BaseModel):
    title: str
    detail: str


class RiskReport(BaseModel):
    risks: list[RiskFinding]


class Requirement(BaseModel):
    """One extracted requirement, after the JD has been checked for it."""

    key: str
    label: str
    mentions: int
    evidence: str


EXTRACT_SYSTEM = """You read job descriptions and list the concrete, checkable requirements they state.

Include technologies, tools, platforms, languages, frameworks, methodologies, certifications and qualifications.
Exclude generic traits — "team player", "excellent communication", "self-starter" — and anything about the company itself.

Rules:
- `label` uses the job description's own wording, and is at most four words.
- `evidence` is a span copied VERBATIM from the job description containing that requirement. Never paraphrase it.
- Never list a requirement the text does not state.
- At most 20 requirements, most important first."""

DIFF_SYSTEM = """You compare a list of job requirements against a candidate's full profile.

For each requirement, decide whether the profile already evidences it.

Rules:
- `present` is true only when the profile text supports the claim. A related skill is not the same skill.
- `evidence` is a span copied VERBATIM from the profile showing where it is claimed. Leave it empty when `present` is false.
- Judge the WHOLE profile, including old roles. A skill used years ago is still a skill the candidate has.
- Return exactly one verdict per requirement, using the requirement's label unchanged."""

RISK_SYSTEM = """You compare a job description against a candidate's profile and report mismatches a human should see before applying.

Report only substantive mismatches: seniority, years of experience, a required qualification the candidate lacks, a different domain, or a location or work mode that conflicts.

Rules:
- `title` is at most six words.
- `detail` is one sentence naming the job's requirement and what the profile shows instead.
- Report nothing you cannot ground in both texts. An empty list is the right answer for a well-matched job.
- At most 5 findings."""


async def rectify(job_id: str) -> dict[str, Any]:
    """Score one job against the profile and persist the result through `server`.

    The match lands with its review gate PENDING. Nothing here selects a keyword —
    that is the user's answer at the interrupt, and the server refuses a resume
    built on keywords they did not tick. (FR-2.5, FR-7.3)
    """
    job = await jobpilot_api.get_job_description(job_id)
    profile = await jobpilot_api.get_profile()

    jd_text = _jd_text(job)
    requirements = await extract_requirements(jd_text)
    present, missing = await split_by_profile(requirements, profile)
    risks = await detect_risks(job, jd_text, profile)

    payload = {
        "jobId": job_id,
        "score": coverage_score(present, missing),
        "present": [{"label": item.label} for item in present],
        "missing": [item.model_dump() for item in missing],
        "risks": [{"key": item.key, "title": item.title, "detail": item.detail} for item in risks],
        "modelName": settings.provenance,
    }
    return await jobpilot_api.write_match(payload)


# --- P5-03: structured keyword extraction ------------------------------------


async def extract_requirements(jd_text: str) -> list[Requirement]:
    """Pull the stated requirements out of a JD, keeping only what the JD backs up."""
    extraction = await generate(
        Extraction,
        f"Job description:\n\n{jd_text}",
        system=EXTRACT_SYSTEM,
    )

    haystack = _flatten(jd_text)
    requirements: list[Requirement] = []
    seen: set[str] = set()

    for keyword in extraction.keywords:
        label = keyword.label.strip()
        if not label or len(label) > 60:
            continue

        # A quote nobody can find in the JD is the screen showing the user something
        # the posting never said, so the requirement is dropped rather than shown
        # with an invented one.
        evidence = _verified_span(keyword.evidence, haystack) or _sentence_with(label, jd_text)
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
                # Counted here rather than taken from the model: how often a word
                # appears is arithmetic, and the screen ranks by it.
                mentions=max(1, _occurrences(label, haystack)),
                evidence=evidence,
            )
        )

    return requirements


# --- P5-04: present / missing diff against the whole profile -----------------


async def split_by_profile(
    requirements: list[Requirement], profile: dict[str, Any]
) -> tuple[list[Requirement], list[Requirement]]:
    """Split the requirements into what the profile already shows and what it does not."""
    if not requirements:
        return [], []

    corpus = profile_corpus(profile)
    flat_profile = _flatten(corpus)

    # A label sitting verbatim in the profile is a fact, not a judgement, so it never
    # reaches the model — and can never be reported Missing by a bad one.
    literal = {item.key for item in requirements if _occurrences(item.label, flat_profile)}
    undecided = [item for item in requirements if item.key not in literal]

    claimed: set[str] = set()
    if undecided:
        listing = "\n".join(f"- {item.label}" for item in undecided)
        diff = await generate(
            Diff,
            f"Requirements:\n{listing}\n\nCandidate profile:\n\n{corpus}",
            system=DIFF_SYSTEM,
        )
        by_key = {item.key: item for item in undecided}
        for verdict in diff.verdicts:
            key = slug(verdict.label)
            # An unsupported "already have it" is the dangerous direction: it hides a
            # keyword the user would otherwise have been offered. Unverifiable
            # evidence sends the requirement back to Missing, where they decide.
            if verdict.present and key in by_key and _verified_span(verdict.evidence, flat_profile):
                claimed.add(key)

    evidenced = literal | claimed
    present = [item for item in requirements if item.key in evidenced]
    missing = [item for item in requirements if item.key not in evidenced]
    return present, missing


# --- P5-05: risk flags -------------------------------------------------------


class Risk(BaseModel):
    key: str
    title: str
    detail: str


async def detect_risks(job: dict[str, Any], jd_text: str, profile: dict[str, Any]) -> list[Risk]:
    """Mismatches the user should see. Surfaced, never selectable — acting on one
    would be a misrepresentation. (FR-2.4)"""
    report = await generate(
        RiskReport,
        f"Job:\n{job.get('title', '')} at {job.get('company', {}).get('name', '')}\n"
        f"Location: {job.get('location', '')}\n"
        f"Experience band: {job.get('experienceBand') or 'not stated'}\n"
        f"Work mode: {job.get('workMode') or 'not stated'}\n\n"
        f"{jd_text}\n\n"
        f"Candidate:\n{profile_digest(profile)}",
        system=RISK_SYSTEM,
    )

    risks: list[Risk] = []
    seen: set[str] = set()
    for finding in report.risks[:5]:
        title, detail = finding.title.strip(), finding.detail.strip()
        key = slug(title)
        if not (title and detail) or key in seen:
            continue
        seen.add(key)
        risks.append(Risk(key=key, title=title, detail=detail))
    return risks


# --- the score ---------------------------------------------------------------


def coverage_score(present: list[Requirement], missing: list[Requirement]) -> int:
    """Keyword coverage, weighted by how often the JD asks for each requirement.

    P5-06 replaces this with JD-embedding similarity once Atlas exists. Until then
    the score is arithmetic over the diff rather than a number the model invents,
    which is the honest version of not having a vector store.
    """
    covered = sum(item.mentions for item in present)
    total = covered + sum(item.mentions for item in missing)
    return round(100 * covered / total) if total else 0


# --- profile and JD text -----------------------------------------------------


def profile_corpus(profile: dict[str, Any]) -> str:
    """Everything the diff may weigh — every role, not just the current one."""
    personal = profile.get("profile") or {}
    parts: list[str] = [
        f"Name: {profile.get('name', '')}",
        f"Current role: {profile.get('role', '')}",
    ]
    if personal.get("headline"):
        parts.append(f"Headline: {personal['headline']}")
    if personal.get("summary"):
        parts.append(f"Summary: {personal['summary']}")

    for entry in profile.get("work", []):
        until = "Present" if entry.get("current") else (entry.get("end") or "")
        parts.append(
            f"\n{entry.get('title', '')} — {entry.get('company', '')} ({entry.get('start', '')} to {until})"
        )
        parts.extend(f"  - {bullet}" for bullet in entry.get("bullets", []))
        for project in entry.get("projects", []):
            parts.append(f"  Project: {project.get('name', '')}")
            parts.extend(f"    - {bullet}" for bullet in project.get("bullets", []))

    groups = profile.get("skill", [])
    if groups:
        parts.append("\nSkills")
        parts.extend(
            f"  {group.get('name', '')}: {', '.join(group.get('items', []))}" for group in groups
        )

    education = profile.get("education", [])
    if education:
        parts.append("\nEducation")
        parts.extend(
            f"  {entry.get('degree', '')}, {entry.get('institution', '')}" for entry in education
        )

    certifications = profile.get("certification", [])
    if certifications:
        parts.append("\nCertifications")
        parts.extend(
            f"  {entry.get('name', '')} — {entry.get('issuer', '')}" for entry in certifications
        )

    return "\n".join(parts)


def profile_digest(profile: dict[str, Any]) -> str:
    """The shorter view the risk step works from: who they are and how long, not
    every bullet they have ever written."""
    personal = profile.get("profile") or {}
    work = profile.get("work", [])
    lines = [
        f"Role: {profile.get('role', '')}",
        f"Headline: {personal.get('headline', '')}",
        f"Location: {personal.get('location', '')}",
        f"Roles held: {len(work)}",
    ]
    lines.extend(
        f"  {entry.get('title', '')} at {entry.get('company', '')} "
        f"({entry.get('start', '')} to {'Present' if entry.get('current') else entry.get('end') or ''})"
        for entry in work
    )
    lines.append(
        "Skills: "
        + "; ".join(
            f"{group.get('name', '')}: {', '.join(group.get('items', []))}"
            for group in profile.get("skill", [])
        )
    )
    lines.extend(
        f"Education: {entry.get('degree', '')}, {entry.get('institution', '')}"
        for entry in profile.get("education", [])
    )
    return "\n".join(lines)


def _jd_text(job: dict[str, Any]) -> str:
    parts = [job.get("jdText", "")]
    if job.get("requirements"):
        parts.append("Requirements:\n" + "\n".join(f"- {line}" for line in job["requirements"]))
    if job.get("responsibilities"):
        parts.append(
            "Responsibilities:\n" + "\n".join(f"- {line}" for line in job["responsibilities"])
        )
    return "\n\n".join(part for part in parts if part)[:MAX_JD_CHARS]


# --- text helpers ------------------------------------------------------------

_WORD_RE = re.compile(r"[^a-z0-9]+")


def slug(value: str) -> str:
    return _WORD_RE.sub("-", value.strip().lower()).strip("-")


def _flatten(value: str) -> str:
    """Lowercased, whitespace-collapsed, so a quote that differs only in line breaks
    still matches the source it was copied from."""
    return re.sub(r"\s+", " ", value).strip().lower()


def _occurrences(needle: str, flat_haystack: str) -> int:
    pattern = re.escape(_flatten(needle))
    return len(re.findall(rf"(?<![a-z0-9]){pattern}(?![a-z0-9])", flat_haystack))


def _verified_span(span: str, flat_source: str) -> str | None:
    """The span, if it really was copied from the source."""
    cleaned = re.sub(r"\s+", " ", span).strip()
    if len(cleaned) < 8:
        return None
    return cleaned if _flatten(cleaned) in flat_source else None


def _sentence_with(label: str, source: str) -> str | None:
    """The JD's own sentence naming the label — the fallback when the model's quote
    cannot be found but the label itself can."""
    flat_label = _flatten(label)
    for sentence in re.split(r"(?<=[.!?\n])\s+", source):
        cleaned = re.sub(r"\s+", " ", sentence).strip()
        if flat_label and flat_label in _flatten(cleaned):
            return cleaned[:300]
    return None


if __name__ == "__main__":
    import asyncio
    import sys

    async def main() -> None:
        job_id = sys.argv[1] if len(sys.argv) > 1 else ""
        if not job_id:
            print("usage: python agents/matching.py <job_id>")
            return
        match = await rectify(job_id)
        print(f"score {match['score']} via {match['modelName']}")
        print("present:", [item["label"] for item in match["present"]])
        print("missing:", [item["label"] for item in match["missing"]])
        print("risks:  ", [item["title"] for item in match["risks"]])

    asyncio.run(main())
