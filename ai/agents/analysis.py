"""Everything done to a stored job after discovery, behind one Analyze button.

Four steps, each standing alone so one failing does not cost the others. The job
page renders the stored markdown itself, so no HTML is produced here:

| step      | writes                                   | model          |
|-----------|------------------------------------------|----------------|
| details   | experience, salary, work mode, job type  | the LLM        |
| embedding | the JD's vector                          | Voyage         |
| techStack | the job's technologies                   | the LLM        |
| match     | score, keywords, risks — via `rectify`,  | the LLM, 2×    |
|           | reusing the techStack step's extraction  |                |

The details step follows the parser's rule: the model proposes, the page decides. An
experience or salary figure not present in the posting verbatim is dropped, and a
work mode or job type needs a word in the text that says so. A field the board
already supplied is never overwritten.

Nothing is paid for twice: each step skips what is already stored — the four details,
the vector, a tech stack already read (even an empty one), your match — and a job with
all of them is skipped whole.
"""

from __future__ import annotations

import asyncio
import re
from collections.abc import Callable
from typing import Any, Literal

from pydantic import BaseModel, Field

from agents import matching
from config.llm import generate
from mcp_servers.jobpilot_api import client
from mcp_servers.jobpilot_api.client import JobPilotApiError
from rag.embeddings import VoyageEmbeddings

DETAIL_FIELDS = ("experienceBand", "salaryText", "workMode", "jobType")

# The same ceiling the match step uses. Past this a JD is boilerplate and legal text.
MAX_JD_CHARS = 12_000

# Words that have to appear in the posting before a work mode or job type is believed.
MODE_WORDS = {
    "remote": r"\bremote\b|work from home|\bwfh\b",
    "hybrid": r"\bhybrid\b",
    "on_site": r"\bon[- ]?site\b|\bin[- ]office\b|work from office|\bwfo\b",
}
TYPE_WORDS = {
    "full_time": r"\bfull[- ]time\b|\bpermanent\b",
    "part_time": r"\bpart[- ]time\b",
    "contract": r"\bcontract(or|ual)?\b|\bfixed[- ]term\b",
    "internship": r"\bintern(ship)?\b",
}

DETAILS_SYSTEM = """You read one job posting and report four facts about the role, only when the posting states them.

Rules:
- Copy `experience` and `salary` from the posting verbatim — the exact words it uses,
  e.g. "6-10 years", "Minimum 8 years of experience", "₹40–55 LPA". Never compute,
  convert, round or combine figures.
- `workMode` is on_site, hybrid or remote; `jobType` is full_time, contract, part_time
  or internship.
- Answer null for anything the posting does not state outright. Do not infer a work
  mode from a city, or a job type from seniority. A guess is worse than null."""


class JobDetails(BaseModel):
    experience: str | None = None
    salary: str | None = None
    workMode: Literal["on_site", "hybrid", "remote"] | None = None
    jobType: Literal["full_time", "contract", "part_time", "internship"] | None = None


class StepResult(BaseModel):
    ok: bool
    note: str | None = None


class AnalysisOutcome(BaseModel):
    """One job's analysis, as a run report shows it."""

    jobId: str
    title: str = ""
    company: str = ""
    score: int | None = None
    steps: dict[str, StepResult] = Field(default_factory=dict)
    # Set when nothing could run at all — no description to analyze.
    error: str | None = None
    # Set when nothing needed to run — the job was analyzed before.
    skipped: str | None = None


# Called with each step as it starts and ends, so a watcher can show progress live.
OnEvent = Callable[[dict[str, Any]], None]


def _ignore(event: dict[str, Any]) -> None:
    return None


async def analyze(job_id: str, on_event: OnEvent = _ignore) -> AnalysisOutcome:
    job = await client.get_job(job_id)
    outcome = AnalysisOutcome(jobId=job_id, title=job["title"], company=job["company"])
    on_event({"type": "job_started", "jobId": job_id, "title": job["title"]})

    async def step(name: str, work: Any) -> StepResult:
        on_event({"type": "step_started", "jobId": job_id, "step": name})
        result = await _step(work)
        return done(name, result)

    def done(name: str, result: StepResult) -> StepResult:
        on_event({"type": "step", "jobId": job_id, "step": name, **result.model_dump()})
        return result

    existing = await _existing_match(job_id)
    if existing is not None:
        outcome.score = existing.get("score")
        if job.get("techStack") is not None:
            outcome.skipped = "already analyzed"
            return outcome

    description = await client.get_description_for_job(job_id)
    text = (description or {}).get("jdText", "").strip()
    if not description or not text:
        outcome.error = "no job description is stored for this job"
        return outcome

    outcome.steps["details"] = await step("details", _details(job, text[:MAX_JD_CHARS]))
    if description.get("hasEmbedding"):
        outcome.steps["embedding"] = done("embedding", StepResult(ok=True, note="already embedded"))
    else:
        outcome.steps["embedding"] = await step(
            "embedding", _embedding(description["id"], text[:MAX_JD_CHARS])
        )

    # Handed from the techStack step to the match, so the posting is extracted once.
    extracted: list[matching.Requirement] = []
    if job.get("techStack") is not None:
        outcome.steps["techStack"] = done("techStack", StepResult(ok=True, note="already read"))
    else:
        outcome.steps["techStack"] = await step(
            "techStack", _tech_stack(job, description, extracted)
        )

    if existing is not None:
        outcome.steps["match"] = done("match", StepResult(ok=True, note="already matched"))
        return outcome
    match: dict[str, Any] = {}
    outcome.steps["match"] = await step("match", _match(job_id, extracted or None, match))
    outcome.score = match.get("score")
    return outcome


async def analyze_many(
    job_ids: list[str],
    on_result: Callable[[AnalysisOutcome], None] | None = None,
    at_once: int = 2,
    on_event: OnEvent = _ignore,
) -> list[AnalysisOutcome]:
    """A few jobs at a time: each match makes three LLM calls, and the hosted model's
    rate limit is the real ceiling, not this machine."""
    slots = asyncio.Semaphore(at_once)

    async def one(job_id: str) -> AnalysisOutcome:
        async with slots:
            outcome = await analyze(job_id, on_event)
        if on_result is not None:
            on_result(outcome)
        return outcome

    return await asyncio.gather(*(one(job_id) for job_id in job_ids))


# --- the steps -----------------------------------------------------------------


async def _existing_match(job_id: str) -> dict[str, Any] | None:
    try:
        return await client.get_match(job_id)
    except JobPilotApiError as error:
        if error.status == 404:
            return None
        raise


async def _step(work: Any) -> StepResult:
    """Run one step; a failure is recorded, not raised — except a dead token, which
    fails every later call the same way and so ends the whole run."""
    try:
        note = await work
    except JobPilotApiError as error:
        if error.status == 401:
            raise
        return StepResult(ok=False, note=str(error)[:200])
    except Exception as error:  # noqa: BLE001 — one step's failure must not stop the rest
        return StepResult(ok=False, note=f"{type(error).__name__}: {error}"[:200])
    return StepResult(ok=True, note=note)


async def _details(job: dict[str, Any], text: str) -> str:
    if all(job.get(field) for field in DETAIL_FIELDS):
        return "all details already known"
    # The tech stack is read with the details — by the capture parser in one call, or by
    # this run's own later step — so a stack already there means the details were read.
    if job.get("techStack") is not None:
        return "already read"
    proposed = await generate(JobDetails, text, system=DETAILS_SYSTEM, max_tokens=512)
    found = verify_details(proposed, text)
    # The board's own values win: only fields the job does not have yet are written.
    changes = {
        field: value
        for field, value in {
            "experienceBand": found.experience,
            "salaryText": found.salary,
            "workMode": found.workMode,
            "jobType": found.jobType,
        }.items()
        if value is not None and not job.get(field)
    }
    if changes:
        await client.update_job(job["id"], changes)
        return "filled " + ", ".join(sorted(changes))
    return "nothing new stated"


async def _embedding(description_id: str, text: str) -> str:
    [vector] = await VoyageEmbeddings().embed_documents([text])
    await client.store_description_embedding(description_id, vector)
    return f"{len(vector)} dimensions"


async def _tech_stack(
    job: dict[str, Any], description: dict[str, Any], into: list[matching.Requirement]
) -> str:
    requirements = await matching.extract_requirements(matching._jd_text(description))
    into.extend(requirements)
    stack = matching.tech_stack(requirements)
    await client.update_job(job["id"], {"techStack": stack})
    return f"{len(stack)} technologies" if stack else "names no technology"


async def _match(
    job_id: str, requirements: list[matching.Requirement] | None, into: dict[str, Any]
) -> str:
    match = await matching.rectify(job_id, requirements)
    into.update(match)
    return f"score {match.get('score')}"


# --- pure helpers, tested directly ------------------------------------------------


def verify_details(proposed: JobDetails, text: str) -> JobDetails:
    flat = _flatten(text)
    return JobDetails(
        experience=proposed.experience if _verbatim(proposed.experience, flat) else None,
        salary=proposed.salary if _verbatim(proposed.salary, flat) else None,
        workMode=proposed.workMode if _said(MODE_WORDS, proposed.workMode, text) else None,
        jobType=proposed.jobType if _said(TYPE_WORDS, proposed.jobType, text) else None,
    )


def _verbatim(value: str | None, flat_text: str) -> bool:
    return bool(value) and _flatten(value) in flat_text


def _said(words: dict[str, str], value: str | None, text: str) -> bool:
    return value is not None and re.search(words[value], text, re.IGNORECASE) is not None


def _flatten(value: str) -> str:
    return " ".join(value.lower().split())


if __name__ == "__main__":
    print(
        verify_details(
            JobDetails(experience="6-10 years", salary="40 LPA", workMode="hybrid"),
            "We need 6-10 years of experience. Hybrid, Bengaluru.",
        )
    )
