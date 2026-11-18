"""Everything done to a stored job after discovery, behind one Analyze button.

Three steps, each standing alone so one failing does not cost the others. The job
page renders the stored markdown itself, so no HTML is produced here:

| step      | writes                                   | model                       |
|-----------|------------------------------------------|-----------------------------|
| techStack | the job's technologies, from the brief   | the LLM, once               |
| details   | experience, salary, work mode, job type  | none: copied from the brief |
| match     | score, keywords, risks, via `rectify`,   | the LLM, once               |
|           | reusing the same brief                   |                             |

The posting is read by the model once. The brief that read carries the tech stack and
the four details, each already checked against the posting, so the details step is a
copy and not a second reading. A field the board already supplied is never overwritten.

Nothing is paid for twice: each step skips what is already stored (the four details,
a tech stack already read, even an empty one, your match) and a job with all of them
is skipped whole.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field

from agents import matching
from agents.details import DETAIL_FIELDS
from mcp_servers.jobpilot_api import client
from mcp_servers.jobpilot_api.client import JobPilotApiError

logger = logging.getLogger(__name__)


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

    # Read once, here, and handed to both later steps.
    briefs: list[matching.Brief] = []
    outcome.steps["techStack"] = await step("techStack", _tech_stack(job, description, briefs))
    brief = briefs[0] if briefs else None
    outcome.steps["details"] = await step("details", _details(job, brief))

    if existing is not None:
        outcome.steps["match"] = done("match", StepResult(ok=True, note="already matched"))
        return outcome
    match: dict[str, Any] = {}
    outcome.steps["match"] = await step("match", _match(job_id, brief, match))
    outcome.score = match.get("score")
    return outcome


async def analyze_many(
    job_ids: list[str],
    on_result: Callable[[AnalysisOutcome], None] | None = None,
    at_once: int = 2,
    on_event: OnEvent = _ignore,
) -> list[AnalysisOutcome]:
    """A few jobs at a time. A local model serves one request at a time, so more than
    this only queues at Ollama while holding more jobs half-done."""
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
        logger.error("analysis step failed: %s", error)
        return StepResult(ok=False, note=str(error)[:200])
    except Exception as error:  # one step's failure must not stop the rest
        logger.exception("analysis step failed")
        return StepResult(ok=False, note=f"{type(error).__name__}: {error}"[:200])
    return StepResult(ok=True, note=note)


async def _tech_stack(
    job: dict[str, Any], description: dict[str, Any], into: list[matching.Brief]
) -> str:
    """The posting's brief, stored or freshly read, and the stack it names."""
    brief = await matching.ensure_brief(description, job)
    into.append(brief)
    if job.get("techStack") is not None:
        return "already read"
    stack = matching.tech_stack(brief.requirements)
    await client.update_job(job["id"], {"techStack": stack})
    return f"{len(stack)} technologies" if stack else "names no technology"


async def _details(job: dict[str, Any], brief: matching.Brief | None) -> str:
    """Copy what the brief read. No model: the brief checked each value against the
    posting when it was built."""
    if all(job.get(field) for field in DETAIL_FIELDS):
        return "all details already known"
    if brief is None:
        return "the posting could not be read"
    # The board's own values win: only fields the job does not have yet are written.
    changes = {
        field: value
        for field, value in brief.details().as_job_fields().items()
        if not job.get(field)
    }
    if changes:
        await client.update_job(job["id"], changes)
        return "filled " + ", ".join(sorted(changes))
    return "nothing new stated"


async def _match(job_id: str, brief: matching.Brief | None, into: dict[str, Any]) -> str:
    match = await matching.rectify(job_id, brief)
    into.update(match)
    return f"score {match.get('score')}"
