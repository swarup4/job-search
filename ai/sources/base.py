"""What every adapter hands back, which of those postings are wanted, and the one
path that writes them.

Tiers 1–3 read structured feeds, so no LLM runs here: the fields are the board's own.
A posting becomes a `Job` and a linked `JobDescription` whose markdown is converted
from the feed's HTML, never composed.
"""

from __future__ import annotations

import hashlib
import os
import re
from datetime import datetime
from typing import Any

from markdownify import markdownify
from pydantic import BaseModel

import config  # noqa: F401 — imported for its .env load
from mcp_servers.jobpilot_api import client

# Fallbacks only. A run scrapes with the account's saved Search targets
# (`/api/preference`); these apply when a field there is empty, and to a dry run.
# The page cap has no saved counterpart, so it always comes from here.
DEFAULT_TITLES = [
    part.strip()
    for part in os.environ.get(
        "SCRAPE_TITLES", "AI,GenAI,Generative,LLM,Agentic,Machine Learning,ML"
    ).split(",")
    if part.strip()
]
DEFAULT_LOCATIONS = [
    part.strip() for part in os.environ.get("SCRAPE_LOCATIONS", "India").split(",") if part.strip()
]
DEFAULT_WORKDAY_MAX_PAGES = int(os.environ.get("SCRAPE_WORKDAY_MAX_PAGES", "5"))

SOURCE = "career_page"


class Filters(BaseModel):
    """What one run keeps. Built once per run and handed to every adapter, so every
    company in a run is searched with the same targets."""

    titles: list[str]
    locations: list[str]
    workdayMaxPages: int

    @classmethod
    def from_preferences(cls, saved: dict[str, Any] | None) -> Filters:
        """The saved `roles` are what titles are matched against. The page cap is not a
        saved preference — it stays with this tier's configuration."""
        saved = saved or {}
        return cls(
            titles=saved.get("roles") or DEFAULT_TITLES,
            locations=saved.get("locations") or DEFAULT_LOCATIONS,
            workdayMaxPages=DEFAULT_WORKDAY_MAX_PAGES,
        )

    def title_wanted(self, title: str) -> bool:
        """Word-bounded, case-insensitive: "AI" matches "AI / ML Engineer" and "Lead AI
        Architect", not "Maintenance"."""
        pattern = r"\b(?:" + "|".join(re.escape(term) for term in self.titles) + r")\b"
        return re.search(pattern, title, re.IGNORECASE) is not None

    def location_wanted(self, *places: str) -> bool:
        return any(want.lower() in place.lower() for place in places for want in self.locations)


class Posting(BaseModel):
    refId: str
    title: str
    company: str
    location: str
    # The board's own country field. The server reads one from `location` without it.
    country: str | None = None
    jobType: str | None = None
    workMode: str | None = None
    postedAt: datetime | None = None
    listingUrl: str
    html: str


class Harvest(BaseModel):
    """One company's pull. `fetched` counts every listing seen, `known` the wanted ones
    already stored and so never fetched again, `failed` the detail fetches that
    errored — so a run report can say how much was looked at."""

    fetched: int = 0
    known: int = 0
    failed: int = 0
    postings: list[Posting] = []


def dedup_hash(posting: Posting) -> str:
    """The company is part of the seed, unlike `job.compute_dedup_hash`'s
    `source|refId`: every source here is `career_page`, and two Workday tenants can
    both issue `R0001`. The cost is that a posting captured through the extension and
    scraped here is stored twice."""
    seed = f"{SOURCE}|{posting.company}|{posting.refId}".lower()
    return hashlib.sha256(seed.encode()).hexdigest()


async def ingest(posting: Posting) -> bool:
    """Write one posting and its description. True when the job was new.

    A job that already exists but lost its description — a run that died between
    the two writes — gets it now, so a re-run repairs rather than skips."""
    created = await client.create_job(
        {
            "refId": posting.refId,
            "title": posting.title,
            "company": posting.company,
            "location": posting.location,
            "country": posting.country,
            "jobType": posting.jobType,
            "workMode": posting.workMode,
            "source": SOURCE,
            "listingUrl": posting.listingUrl,
            "postedAt": posting.postedAt.isoformat() if posting.postedAt else None,
            "dedupHash": dedup_hash(posting),
        }
    )
    job_id = created["id"]
    if created["duplicate"] and await client.get_description_for_job(job_id) is not None:
        return False

    markdown = markdownify(posting.html, heading_style="ATX").strip()
    description = await client.create_description(
        {
            "url": posting.listingUrl,
            "pageTitle": posting.title,
            "markdown": markdown,
            "region": "feed",
            "textLength": len(_visible_text(posting.html)),
            "links": [posting.listingUrl],
        }
    )
    if not description["duplicate"]:
        await client.link_description(description["id"], job_id)
    return not created["duplicate"]


def _visible_text(html: str) -> str:
    return " ".join(re.sub(r"<[^>]+>", " ", html).split())
