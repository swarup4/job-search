"""P3-14 — turn a captured page into a `Job`.

A capture is markdown of a career page. This reads it once — title, company, location,
the four details and the posting's brief, in one model call — writes the listing row
the board shows, links the two, and stores the brief on the description. Analyze later
has only the match left to do: the brief it needs is already there. Discovery by
connector (`P3-02`/`P3-03`) will write the same shape without an LLM; this is the path
for pages a human captured.

Every field written has to be findable in the page. A title or a company the model
composed rather than copied is the same failure as an invented resume keyword, so the
checks here are `matching.verified_brief`'s: the model proposes, the text decides.
The page is cleaned first (cleaning.py) and checked against the cleaned text, which is
the text the model was shown.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

from pydantic import BaseModel, Field

from agents import matching
from agents.cleaning import POSTING_CHARS, clean_posting
from agents.details import JobType, WorkMode
from agents.inventory import KIND_RULE
from agents.matching import QUOTE, SHORT, BriefDraft, ExtractedKeyword
from config.llm import DEFAULT, UNTRUSTED_RULE, as_document, generate
from mcp_servers.jobpilot_api import client

logger = logging.getLogger(__name__)

# What a captured page may take of the prompt, after cleaning. A longer page loses
# whole sections — benefits, legal text, "similar jobs" — before its requirements.
MAX_PAGE_CHARS = POSTING_CHARS

# A posting names a handful of technologies. A list longer than this is the model
# restating the JD, and a filter every job matches is not a filter.
MAX_STACK = 20

# Bumped when PARSE_SYSTEM or the parsed shape changes. Recorded with the call's usage.
# 2: the parse also returns the brief (requirements with evidence, and constraints).
PARSE_VERSION = 2

PARSE_SYSTEM = f"""You read a career page, captured as markdown, and pull out the posting it advertises.

{UNTRUSTED_RULE}

Rules:
- Copy values from the page. Never translate, expand or tidy them — `title` and `company` must
  appear in the page verbatim.
- `isPosting` is false when the page is a job *list*, a search page, a login wall, or anything
  that is not one specific opening. Say so rather than guessing at fields.
- `refId` is the board's own requisition id if the page shows one, else null.

`requirements` — the concrete, checkable requirements the posting states: technologies, tools,
platforms, languages, frameworks, methodologies, certifications and qualifications. Exclude
generic traits ("team player", "excellent communication") and anything about the company itself.
- `label` uses the page's own wording, at most four words. Prefer the shortest form the page uses.
- {KIND_RULE}
  Activities and qualities are never "tech", even when the posting stresses them — "production
  deployment", "observability", "compliance", "governance", "best practices". If you would not
  install it, import it or sign up for it, it is not "tech".
- `evidence` is a span copied VERBATIM from the page containing the requirement. Never
  paraphrase, never join spans.
- Never list a requirement the page does not state. At most 20, most important first.
- Years of experience and seniority are constraints, never requirements.

Constraints and details — null unless the page states it outright:
- `seniority`: the level word it uses, e.g. "Senior", "Lead", "Staff".
- `minYears`: the minimum years of experience, as a number.
- `locationRule`: its location or relocation requirement, copied verbatim.
- `workMode`: on_site, hybrid or remote. `jobType`: full_time, contract, part_time or internship.
- `experience` and `salary`: copied verbatim — the exact words the page uses, e.g. "6-10 years",
  "Minimum 8 years of experience", "₹40–55 LPA". Never compute, convert, round or combine
  figures."""


class ParsedPosting(BaseModel):
    isPosting: bool
    title: str = Field(default="", max_length=200)
    company: str = Field(default="", max_length=120)
    location: str = Field(default="", max_length=200)
    refId: str | None = Field(default=None, max_length=SHORT)
    requirements: list[ExtractedKeyword] = Field(default_factory=list, max_length=25)
    seniority: str | None = Field(default=None, max_length=40)
    minYears: int | None = None
    locationRule: str | None = Field(default=None, max_length=200)
    workMode: WorkMode | None = None
    jobType: JobType | None = None
    experience: str | None = Field(default=None, max_length=SHORT)
    salary: str | None = Field(default=None, max_length=SHORT)

    def brief_draft(self) -> BriefDraft:
        """The brief's half of the reading, in the shape the brief call returns."""
        return BriefDraft(
            requirements=[
                ExtractedKeyword(
                    label=item.label[:SHORT], kind=item.kind, evidence=item.evidence[:QUOTE]
                )
                for item in self.requirements
            ],
            seniority=self.seniority,
            minYears=self.minYears,
            locationRule=self.locationRule,
            workMode=self.workMode,
            experience=self.experience,
            salary=self.salary,
            jobType=self.jobType,
        )


class ParseOutcome(BaseModel):
    """What happened to one capture, so a batch run reads as a report."""

    descriptionId: str
    parsed: bool
    jobId: str | None = None
    duplicate: bool = False
    reason: str | None = None


async def parse_description(description_id: str) -> ParseOutcome:
    """Read one capture, write the job it describes, link them, and store its brief."""
    description = await client.get_description(description_id)
    cleaned = clean_posting(description.get("jdText") or "", MAX_PAGE_CHARS)
    page = cleaned.text
    if not page.strip():
        await client.set_description_status(description_id, "discarded")
        return ParseOutcome(
            descriptionId=description_id, parsed=False, reason="capture holds no text"
        )

    posting = await generate(
        ParsedPosting,
        as_document("career_page", page),
        system=PARSE_SYSTEM,
        version=PARSE_VERSION,
    )

    flat = _flatten(page)
    if not posting.isPosting:
        await client.set_description_status(description_id, "discarded")
        return ParseOutcome(
            descriptionId=description_id, parsed=False, reason="not a single posting"
        )

    title = _verified(posting.title, flat)
    company = _verified(posting.company, flat)
    if title is None or company is None:
        # Left `raw` on purpose: the page may well be a posting this model read
        # badly, and discarding it would hide that behind a status.
        missing = "title" if title is None else "company"
        return ParseOutcome(
            descriptionId=description_id,
            parsed=False,
            reason=f"{missing} is not present in the captured page",
        )

    payload: dict[str, Any] = {
        "title": title,
        "company": company,
        "location": _location(posting.location, flat),
        "source": "career_page",
        "listingUrl": description.get("url"),
    }
    if posting.refId and _flatten(posting.refId) in flat:
        payload["refId"] = posting.refId
    # The same checks the brief call applies, so a capture never has to be read twice:
    # quotes verbatim, figures verbatim, and a work mode or job type only when a word
    # says so.
    brief = matching.verified_brief(posting.brief_draft(), page, cleaned.flagged)
    payload.update(brief.details().as_job_fields())

    created = await client.create_job(payload)
    job_id = created["id"]
    await client.link_description(description_id, job_id)
    # Stored on the capture, so scoring this job later starts from the brief instead of
    # sending the page to a model a second time.
    await client.store_brief(description_id, matching.brief_payload(brief, DEFAULT.provenance))
    # A job that already had a stack keeps it: the listing is shared, and a second
    # capture of it is not a reason to rewrite what another run read.
    if not created.get("duplicate") or (await client.get_job(job_id)).get("techStack") is None:
        stack = _verified_stack(matching.tech_stack(brief.requirements), flat)
        await client.update_job(job_id, {"techStack": stack})
    return ParseOutcome(
        descriptionId=description_id,
        parsed=True,
        jobId=job_id,
        duplicate=bool(created.get("duplicate")),
    )


async def parse_pending(limit: int = 25) -> list[ParseOutcome]:
    """Every capture nobody has parsed yet. One failure does not stop the batch."""
    outcomes: list[ParseOutcome] = []
    for description in await client.list_raw_descriptions(limit=limit):
        try:
            outcomes.append(await parse_description(description["id"]))
        except Exception as exc:  # a bad page must not end the run
            logger.exception("parsing description %s failed", description["id"])
            outcomes.append(
                ParseOutcome(
                    descriptionId=description["id"],
                    parsed=False,
                    reason=f"{type(exc).__name__}: {exc}",
                )
            )
    return outcomes


# --- text checks -------------------------------------------------------------


def _flatten(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().lower()


def _verified(value: str, flat_page: str) -> str | None:
    """The value, if the page really contains it."""
    cleaned = re.sub(r"\s+", " ", value).strip()
    if not cleaned:
        return None
    return cleaned if _flatten(cleaned) in flat_page else None


def _location(value: str, flat_page: str) -> str:
    """Looser than title and company: a page says "Bengaluru, Karnataka, India" and
    the model answers "Bengaluru, India", which is the same place written shorter.
    One part having to match keeps an invented city out without failing the parse."""
    cleaned = re.sub(r"\s+", " ", value).strip()
    if not cleaned:
        return ""
    if _flatten(cleaned) in flat_page:
        return cleaned
    parts = [part.strip() for part in cleaned.split(",") if part.strip()]
    return cleaned if any(_flatten(part) in flat_page for part in parts) else ""


def _verified_stack(tokens: list[str], flat_page: str) -> list[str]:
    """Only technologies the page names, deduped, order kept, capped. A stack the model
    knows the role "usually" wants is exactly what must not reach the listing filter.

    The cap is a blunt second line: the prompt asks for technologies and the page check
    catches inventions, but neither stops a model from restating half the posting in
    words the page does contain."""
    kept: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        cleaned = token.strip()
        flat = _flatten(cleaned)
        if not flat or flat in seen:
            continue
        if re.search(rf"(?<![a-z0-9]){re.escape(flat)}(?![a-z0-9])", flat_page):
            kept.append(cleaned)
            seen.add(flat)
        if len(kept) == MAX_STACK:
            break
    return kept


if __name__ == "__main__":

    async def main() -> None:
        for outcome in await parse_pending():
            state = f"job {outcome.jobId}" if outcome.parsed else f"skipped — {outcome.reason}"
            print(f"{outcome.descriptionId}  {state}")

    asyncio.run(main())
