"""Workday — the platform behind 41 of the companies in the sheet.

The list is `POST /wday/cxs/{tenant}/{site}/jobs`, 20 at a time; the JD is a second
call per posting. Workday's search is loose — "LLM" in India still fills the 2,000
result cap — so titles are matched here, and paging stops at the first page with
nothing wanted on it. Results come back by relevance, so that page is where the
matches have run out.
"""

from __future__ import annotations

import asyncio
import re
from collections.abc import Awaitable, Callable, Iterator
from datetime import UTC, datetime
from html import unescape
from typing import Any

from sources.base import Filters, Harvest, Posting
from sources.http import Fetcher, RobotsDisallowed

# Workday answers 400 to anything larger.
PAGE_SIZE = 20

JOB_TYPES = {"full time": "full_time", "part time": "part_time"}
WORK_MODES = {"remote": "remote", "hybrid": "hybrid", "on-site": "on_site", "onsite": "on_site"}


async def fetch(
    source: dict[str, Any],
    http: Fetcher,
    is_stored: Callable[[str], Awaitable[bool]],
    filters: Filters,
    limit: int | None = None,
) -> Harvest:
    """`is_stored` answers whether a listing URL is already a stored description. A
    stored posting is not fetched again: a daily re-run would otherwise re-download
    every detail only to be told it is a duplicate. `filters` is the run's Search
    targets — one search per title, capped at `workdayMaxPages` pages each. `limit` is
    how many new postings the run can still take: no more details than that are
    fetched."""
    settings = source["config"]
    tenant, site = settings["tenant"], settings["site"]
    origin = f"https://{tenant}.{settings['wd']}.myworkdayjobs.com"
    api = f"{origin}/wday/cxs/{tenant}/{site}"

    # The API path sits outside the site path robots.txt names, so the file never
    # forbids it literally. A disallowed site path is still the tenant saying no.
    if not await http.allowed(f"{origin}/{site}/"):
        raise RobotsDisallowed(f"{origin}/{site}/")

    first = await http.post_json(f"{api}/jobs", _search("", {}, 0))
    facets = _country_facet(first.get("facets", []), filters)

    harvest = Harvest()
    paths: set[str] = set()
    for keyword in filters.titles:
        total = 0
        for page in range(filters.workdayMaxPages):
            data = await http.post_json(f"{api}/jobs", _search(keyword, facets, page * PAGE_SIZE))
            # Only the first page carries the real total; later pages say 0.
            total = total or data.get("total", 0)
            listings = data.get("jobPostings", [])
            harvest.fetched += len(listings)
            hits = [
                row["externalPath"]
                for row in listings
                if filters.title_wanted(row.get("title", ""))
            ]
            paths.update(hits)
            if not hits or (page + 1) * PAGE_SIZE >= total:
                break

    # A skill search keeps every result for now: whether it counts is decided on the
    # description, which only the detail carries. Fewer pages, since each one costs.
    by_skill: set[str] = set()
    for keyword in filters.skills:
        total = 0
        for page in range(filters.skillMaxPages):
            data = await http.post_json(f"{api}/jobs", _search(keyword, facets, page * PAGE_SIZE))
            total = total or data.get("total", 0)
            listings = data.get("jobPostings", [])
            harvest.fetched += len(listings)
            by_skill.update(row["externalPath"] for row in listings)
            if not listings or (page + 1) * PAGE_SIZE >= total:
                break
    by_skill -= paths

    # Workday's `externalUrl` is the site URL plus the listing's path, which is how a
    # stored posting is recognised before its detail is fetched. A tenant that builds
    # it differently is never recognised, and is simply fetched as before.
    # Title matches first, so a limited run spends its budget on the surest ones.
    ordered = sorted(paths) + sorted(by_skill)
    stored = await asyncio.gather(*(is_stored(f"{origin}/{site}{path}") for path in ordered))
    fresh = [path for path, known in zip(ordered, stored, strict=True) if not known]
    harvest.known = len(ordered) - len(fresh)
    if limit is not None:
        fresh = fresh[:limit]

    details = await asyncio.gather(
        *(http.get_json(f"{api}{path}") for path in fresh), return_exceptions=True
    )
    for path, detail in zip(fresh, details, strict=True):
        if isinstance(detail, BaseException):
            harvest.failed += 1
            continue
        posting = _posting(detail["jobPostingInfo"], source["name"], filters)
        if posting is None:
            continue
        if path in by_skill:
            # Found only by a skill search: kept when its description names a skill.
            if not filters.skill_wanted(_text(posting.html)):
                continue
            harvest.bySkill += 1
        harvest.postings.append(posting)
    return harvest


def _text(html: str) -> str:
    """The description without its markup, so a skill split by a tag still reads."""
    return unescape(re.sub(r"<[^>]+>", " ", html))


def _search(text: str, facets: dict[str, list[str]], offset: int) -> dict[str, Any]:
    return {"appliedFacets": facets, "limit": PAGE_SIZE, "offset": offset, "searchText": text}


def _country_facet(facets: list[dict[str, Any]], filters: Filters) -> dict[str, list[str]]:
    """The tenant's country facet, narrowed to the wanted countries. Tenants name it
    differently (`locationCountry`, `Location_Country`) and some nest it a level
    down, so it is found by name rather than assumed. None found means filtering
    falls to `_posting` alone, which it always checks anyway."""
    for facet in _flatten(facets):
        if "country" not in facet.get("facetParameter", "").lower():
            continue
        ids = [
            v["id"]
            for v in facet.get("values", [])
            if filters.location_wanted(v.get("descriptor", ""))
        ]
        if ids:
            return {facet["facetParameter"]: ids}
    return {}


def _flatten(facets: list[dict[str, Any]]) -> Iterator[dict[str, Any]]:
    for facet in facets:
        values = facet.get("values", [])
        if values and "facetParameter" in values[0]:
            yield from _flatten(values)
        else:
            yield facet


def _posting(info: dict[str, Any], company: str, filters: Filters) -> Posting | None:
    country = (info.get("country") or {}).get("descriptor", "")
    places = [p for p in [info.get("location", ""), *info.get("additionalLocations", [])] if p]
    if not filters.location_wanted(country, *places):
        return None

    location = "; ".join(places)
    if country and country not in location:
        location = f"{location}, {country}" if location else country

    started = info.get("startDate")
    return Posting(
        refId=info.get("jobReqId") or info["jobPostingId"],
        title=info["title"],
        company=company,
        location=location,
        country=country or None,
        jobType=JOB_TYPES.get((info.get("timeType") or "").lower()),
        workMode=WORK_MODES.get((info.get("remoteType") or "").lower()),
        postedAt=datetime.fromisoformat(started).replace(tzinfo=UTC) if started else None,
        listingUrl=info["externalUrl"],
        html=info.get("jobDescription", ""),
    )


if __name__ == "__main__":
    ACCENTURE = {
        "name": "Accenture",
        "config": {"tenant": "accenture", "wd": "wd103", "site": "AccentureCareers"},
    }

    async def nothing_stored(url: str) -> bool:
        return False

    async def main() -> None:
        """A dry run: pulls and filters for real, writes nothing."""
        async with Fetcher() as http:
            harvest = await fetch(ACCENTURE, http, nothing_stored, Filters.from_preferences(None))
        print(f"{harvest.fetched} listings seen, {len(harvest.postings)} wanted")
        for posting in harvest.postings[:15]:
            print(f"  {posting.refId:<24} {posting.title}  —  {posting.location}")

    asyncio.run(main())
