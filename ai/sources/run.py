"""One scrape over every enabled career source, reported per company.

Whoever calls `run_all()` must have called `client.set_token()` first: the registry
is read and the jobs are written as the signed-in user, and this tier has nothing
to sign in with.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

import httpx

from mcp_servers.jobpilot_api import client
from mcp_servers.jobpilot_api.client import JobPilotApiError
from sources import workday
from sources.base import Filters, Harvest, ingest
from sources.http import Fetcher, RobotsDisallowed

# The last argument is how many new postings the run can still take (None: no limit),
# so an adapter can stop fetching details once the run has what it asked for.
Adapter = Callable[
    [dict[str, Any], Fetcher, Callable[[str], Awaitable[bool]], Filters, int | None],
    Awaitable[Harvest],
]

ADAPTERS: dict[str, Adapter] = {"workday": workday.fetch}

# Companies are on different hosts, so a few at once costs no site anything; the
# per-host cap in `Fetcher` still holds inside each one.
COMPANIES_AT_ONCE = 4


class Budget:
    """How many more new jobs this run may store, shared by every company in it. `None`
    is no limit. Companies run a few at once, so one checks it before each write."""

    def __init__(self, limit: int | None) -> None:
        self.left = limit

    @property
    def spent(self) -> bool:
        return self.left is not None and self.left <= 0

    def use(self) -> None:
        if self.left is not None:
            self.left -= 1


async def run_source(
    source: dict[str, Any], http: Fetcher, filters: Filters, budget: Budget | None = None
) -> dict[str, Any]:
    budget = budget or Budget(None)
    result: dict[str, Any] = {"fetched": 0, "matched": 0, "new": 0, "duplicate": 0, "failed": 0}
    if budget.spent:
        return {**result, "skipped": True}
    try:
        harvest = await ADAPTERS[source["platform"]](
            source, http, client.description_stored, filters, budget.left
        )
    except RobotsDisallowed as refused:
        return {**result, "blocked": True, "error": str(refused)}
    except JobPilotApiError:
        # The stored-check is a call to the server, so a dead token surfaces here
        # first. That ends the run, not just this company.
        raise
    except (httpx.HTTPError, KeyError, ValueError) as error:
        return {**result, "error": f"{type(error).__name__}: {error}"[:300]}

    result.update(
        fetched=harvest.fetched,
        matched=harvest.known + len(harvest.postings),
        duplicate=harvest.known,
        failed=harvest.failed,
        bySkill=harvest.bySkill,
    )
    for posting in harvest.postings:
        # Another company may have taken the last of the limit while this one fetched.
        if budget.spent:
            break
        try:
            new = await ingest(posting)
        except JobPilotApiError as error:
            # No token fails every write the same way; that is the run's problem,
            # not this posting's.
            if error.status == 401:
                raise
            result["failed"] += 1
            result["error"] = str(error)[:300]
            continue
        result["new" if new else "duplicate"] += 1
        if new:
            budget.use()
    return result


async def run_all(
    sources: list[dict[str, Any]] | None = None,
    filters: Filters | None = None,
    on_result: Callable[[str, dict[str, Any]], None] | None = None,
    limit: int | None = None,
) -> list[tuple[str, dict[str, Any]]]:
    """`sources` defaults to every enabled one, `filters` to the account's saved
    Search targets. `on_result` hears each company as it finishes, which is how a
    caller shows progress on a run that takes minutes. `limit` stops the run once that
    many new jobs are stored; companies not reached by then are reported skipped."""
    if sources is None:
        sources = await client.list_career_sources(enabled=True)
    if filters is None:
        filters = Filters.from_preferences(await client.get_preferences())
    slots = asyncio.Semaphore(COMPANIES_AT_ONCE)
    budget = Budget(limit)

    async with Fetcher() as http:

        async def one(source: dict[str, Any]) -> tuple[str, dict[str, Any]]:
            async with slots:
                result = await run_source(source, http, filters, budget)
            # A skipped company was not scraped; it keeps the result of its last real run.
            if not result.get("skipped"):
                await client.record_source_result(source["id"], result)
            if on_result is not None:
                on_result(source["name"], result)
            return source["name"], result

        return await asyncio.gather(*(one(source) for source in sources))
