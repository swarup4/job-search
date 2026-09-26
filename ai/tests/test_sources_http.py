"""The fetcher is where respect_robots is enforced, so its failure direction matters:
every unclear answer from a site has to read as "no"."""

from __future__ import annotations

import httpx
import pytest

from sources import http as http_module
from sources.http import Fetcher, RobotsDisallowed

ROBOTS = "\nUser-agent: *\nDisallow: /panwexternalcareers/\nDisallow: /refreshFacet/"


def transport(robots: httpx.Response, api: list[httpx.Response] | None = None):
    """Serves robots.txt, then the queued API responses in order, and records every
    request so a test can prove a refused URL was never fetched."""
    queue = list(api or [])
    seen: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path == "/robots.txt":
            return robots
        return queue.pop(0)

    return httpx.MockTransport(handle), seen


async def test_a_disallowed_path_is_never_requested() -> None:
    mock, seen = transport(httpx.Response(200, text=ROBOTS))
    async with Fetcher(transport=mock) as http:
        with pytest.raises(RobotsDisallowed):
            await http.get_json("https://panw.example/panwexternalcareers/job/1")
    assert [r.url.path for r in seen] == ["/robots.txt"]


async def test_robots_is_asked_for_as_text() -> None:
    mock, seen = transport(httpx.Response(200, text=ROBOTS))
    async with Fetcher(transport=mock) as http:
        await http.allowed("https://panw.example/anything")
    assert seen[0].headers["Accept"] == "text/plain"


@pytest.mark.parametrize("status", [401, 403, 406, 500, 503])
async def test_a_refused_robots_file_forbids_everything(status: int) -> None:
    # 406 is what Workday answers a robots.txt request that asks for JSON. Reading
    # it as "no file" once let a disallowed tenant through.
    mock, _ = transport(httpx.Response(status))
    async with Fetcher(transport=mock) as http:
        assert not await http.allowed("https://site.example/jobs")


@pytest.mark.parametrize("status", [404, 410])
async def test_a_missing_robots_file_permits_everything(status: int) -> None:
    mock, _ = transport(httpx.Response(status))
    async with Fetcher(transport=mock) as http:
        assert await http.allowed("https://site.example/jobs")


async def test_an_unreachable_robots_file_forbids_everything() -> None:
    def fail(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route", request=request)

    async with Fetcher(transport=httpx.MockTransport(fail)) as http:
        assert not await http.allowed("https://site.example/jobs")


@pytest.mark.parametrize("status", [429, 500, 503])
async def test_a_transient_failure_is_retried(monkeypatch: pytest.MonkeyPatch, status: int) -> None:
    monkeypatch.setattr(http_module, "_backoff", lambda response, attempt: 0)
    mock, seen = transport(
        httpx.Response(404),
        [httpx.Response(status), httpx.Response(200, json={"total": 3})],
    )
    async with Fetcher(transport=mock) as http:
        assert await http.post_json("https://site.example/jobs", {}) == {"total": 3}
    assert len([r for r in seen if r.url.path == "/jobs"]) == 2
