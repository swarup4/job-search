"""P3-14 — turn a captured page into a `Job`.

A capture is markdown of a career page. This reads it and writes the listing row the
board shows, then links the two. Discovery by connector (`P3-02`/`P3-03`) will write
the same shape without an LLM; this is the path for pages a human captured.

Every field written has to be findable in the page. A title or a company the model
composed rather than copied is the same failure as an invented resume keyword, so the
checks here mirror `matching.extract_requirements`: the model proposes, the text
decides.
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field

from config.llm import generate
from mcp_servers.jobpilot_api import client

# A posting is a few thousand characters. Past this it is a listing page or a nav
# dump, and the tail adds noise rather than signal.
MAX_PAGE_CHARS = 16_000

# A posting names a handful of technologies. A list longer than this is the model
# restating the JD, and a filter every job matches is not a filter.
MAX_STACK = 20

JOB_TYPES = {"full_time", "contract", "part_time", "internship"}
WORK_MODES = {"on_site", "hybrid", "remote"}

PARSE_SYSTEM = """You read a career page, captured as markdown, and pull out the posting it advertises.

Rules:
- Copy values from the page. Never translate, expand or tidy them — `title` and `company` must
  appear in the page verbatim.
- `isPosting` is false when the page is a job *list*, a search page, a login wall, or anything
  that is not one specific opening. Say so rather than guessing at fields.
- `requirements` is the technology stack, and nothing else. A name you could put on a tool,
  language, framework, database, cloud service or protocol: "Python", "Kubernetes", "PostgreSQL",
  "LangGraph", "AWS".
  Exclude activities and qualities even when the posting stresses them — "production deployment",
  "observability", "compliance", "auditability", "risk controls", "governance", "planning",
  "reasoning", "best practices" are NOT technologies and must not appear. If you would not
  install it, import it or sign up for it, leave it out.
  Prefer the shortest form the page uses, and return at most 20.
- `jobType` is one of full_time, contract, part_time, internship, or null.
- `workMode` is one of on_site, hybrid, remote, or null.
- `refId` is the board's own requisition id if the page shows one, else null."""


class ParsedPosting(BaseModel):
    isPosting: bool
    title: str = ""
    company: str = ""
    location: str = ""
    jobType: str | None = None
    workMode: str | None = None
    refId: str | None = None
    requirements: list[str] = Field(default_factory=list)


class ParseOutcome(BaseModel):
    """What happened to one capture, so a batch run reads as a report."""

    descriptionId: str
    parsed: bool
    jobId: str | None = None
    duplicate: bool = False
    reason: str | None = None


async def parse_description(description_id: str) -> ParseOutcome:
    """Read one capture, write the job it describes, and link them."""
    description = await client.get_description(description_id)
    page = (description.get("jdText") or "")[:MAX_PAGE_CHARS]
    if not page.strip():
        await client.set_description_status(description_id, "discarded")
        return ParseOutcome(
            descriptionId=description_id, parsed=False, reason="capture holds no text"
        )

    posting = await generate(
        ParsedPosting,
        f"Career page:\n\n{page}",
        system=PARSE_SYSTEM,
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
    if posting.jobType in JOB_TYPES:
        payload["jobType"] = posting.jobType
    if posting.workMode in WORK_MODES:
        payload["workMode"] = posting.workMode

    created = await client.create_job(payload)
    job_id = created["id"]
    await client.link_description(description_id, job_id)
    # The stack is parsed out of the prose, so it is stored with the prose.
    await client.update_description(
        description_id, {"requirements": _verified_stack(posting.requirements, flat)}
    )
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
        except Exception as exc:  # noqa: BLE001 — a bad page must not end the run
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
    import asyncio

    async def main() -> None:
        for outcome in await parse_pending():
            state = f"job {outcome.jobId}" if outcome.parsed else f"skipped — {outcome.reason}"
            print(f"{outcome.descriptionId}  {state}")

    asyncio.run(main())
