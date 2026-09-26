"""The one HTTP client every adapter fetches through.

robots.txt is checked here, inside every request, rather than left to each adapter:
`DiscoveryPreferences.respect_robots` is `Literal[True]`, so there is no code path
that fetches a disallowed URL. Politeness is per host — at most `MAX_PER_HOST`
requests in flight, and a 429 or a transient 5xx backs off rather than retrying at once.
"""

from __future__ import annotations

import asyncio
import os
from types import TracebackType
from typing import Any, Self
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx

import config  # noqa: F401 — imported for its .env load

USER_AGENT = os.environ.get("SCRAPE_USER_AGENT", "JobPilot/1.0 (personal job-search assistant)")
MAX_PER_HOST = int(os.environ.get("SCRAPE_MAX_PER_HOST", "2"))
TIMEOUT = float(os.environ.get("SCRAPE_TIMEOUT", "30"))
ATTEMPTS = 3
# Workday answers the odd request with a 500 that succeeds on the next try.
RETRY_STATUSES = {429, 500, 502, 503, 504}
MAX_BACKOFF = 30.0


class RobotsDisallowed(RuntimeError):
    """A standing answer from the site, not a failure: retrying will not change it."""

    def __init__(self, url: str) -> None:
        self.url = url
        super().__init__(f"robots.txt disallows {url}")


class Fetcher:
    """One per run. The robots cache lives exactly as long as the run does, so a
    site that changes its rules is re-read next time."""

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._client = httpx.AsyncClient(
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            timeout=TIMEOUT,
            follow_redirects=True,
            transport=transport,
        )
        self._robots: dict[str, RobotFileParser] = {}
        self._slots: dict[str, asyncio.Semaphore] = {}

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self._client.aclose()

    async def allowed(self, url: str) -> bool:
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        if origin not in self._robots:
            self._robots[origin] = await self._read_robots(origin, parts.netloc)
        return self._robots[origin].can_fetch(USER_AGENT, url)

    async def get_json(self, url: str, **kwargs: Any) -> Any:
        return (await self._send("GET", url, **kwargs)).json()

    async def post_json(self, url: str, body: dict[str, Any]) -> Any:
        return (await self._send("POST", url, json=body)).json()

    async def _read_robots(self, origin: str, host: str) -> RobotFileParser:
        parser = RobotFileParser()
        try:
            async with self._slot(host):
                # The client's default Accept is JSON, and Workday answers a JSON
                # request for robots.txt with a 406.
                response = await self._client.get(
                    f"{origin}/robots.txt", headers={"Accept": "text/plain"}
                )
        except httpx.HTTPError:
            # No answer is not permission.
            parser.disallow_all = True
            return parser

        # Only a file that is not there permits everything. Any other refusal — an
        # auth wall, a 406, a 5xx — is read as "no", since reading it as "yes" is the
        # one mistake respect_robots exists to rule out.
        if response.status_code in (404, 410):
            parser.allow_all = True
        elif response.status_code >= 400:
            parser.disallow_all = True
        else:
            parser.parse(response.text.splitlines())
        return parser

    async def _send(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        if not await self.allowed(url):
            raise RobotsDisallowed(url)

        host = urlsplit(url).netloc
        for attempt in range(ATTEMPTS):
            async with self._slot(host):
                response = await self._client.request(method, url, **kwargs)
            if response.status_code not in RETRY_STATUSES or attempt == ATTEMPTS - 1:
                break
            await asyncio.sleep(_backoff(response, attempt))

        response.raise_for_status()
        return response

    def _slot(self, host: str) -> asyncio.Semaphore:
        return self._slots.setdefault(host, asyncio.Semaphore(MAX_PER_HOST))


def _backoff(response: httpx.Response, attempt: int) -> float:
    retry_after = response.headers.get("Retry-After", "")
    delay = float(retry_after) if retry_after.isdigit() else 2.0 ** (attempt + 1)
    return min(delay, MAX_BACKOFF)


if __name__ == "__main__":

    async def main() -> None:
        async with Fetcher() as http:
            for url in (
                "https://accenture.wd103.myworkdayjobs.com/AccentureCareers/",
                "https://paloaltonetworks.wd5.myworkdayjobs.com/panwexternalcareers/",
            ):
                print(f"{'allowed   ' if await http.allowed(url) else 'disallowed'}  {url}")

    asyncio.run(main())
