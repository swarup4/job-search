"""The Workday adapter against response shapes recorded from accenture.wd103 on
2026-09-25, trimmed to the fields it reads."""

from __future__ import annotations

from typing import Any

import pytest

from sources import workday
from sources.base import Filters
from sources.http import RobotsDisallowed

SOURCE = {
    "name": "Accenture",
    "config": {"tenant": "accenture", "wd": "wd103", "site": "AccentureCareers"},
}
API = "https://accenture.wd103.myworkdayjobs.com/wday/cxs/accenture/AccentureCareers"
INDIA = "c4f78be1a8f14da0ab49ce1162348a5e"

# Accenture nests the country facet one level down, under `locationMainGroup`.
FACETS = [
    {"facetParameter": "timeType", "values": [{"descriptor": "Full time", "id": "ft"}]},
    {
        "facetParameter": "locationMainGroup",
        "values": [
            {
                "facetParameter": "locationCountry",
                "descriptor": "Country",
                "values": [
                    {"descriptor": "India", "id": INDIA, "count": 2114},
                    {"descriptor": "Mexico", "id": "mx", "count": 300},
                ],
            },
            {"facetParameter": "locations", "descriptor": "City", "values": []},
        ],
    },
]


def listing(title: str, path: str) -> dict[str, Any]:
    return {"title": title, "externalPath": path, "postedOn": "Posted Today", "bulletFields": []}


def detail(title: str, path: str, **overrides: Any) -> dict[str, Any]:
    info = {
        "title": title,
        "jobDescription": "<b>Project Role :</b> AI / ML Engineer<br><p>Build RAG pipelines.</p>",
        "location": "Hyderabad",
        "startDate": "2026-09-24",
        "timeType": "Full time",
        "jobReqId": f"REQ{path[-1]}",
        "jobPostingId": path.rsplit("/", 1)[-1],
        "country": {"descriptor": "India", "id": INDIA},
        "externalUrl": f"https://accenture.wd103.myworkdayjobs.com/AccentureCareers{path}",
    }
    return {"jobPostingInfo": {**info, **overrides}}


class FakeFetcher:
    """Answers searches from a page list keyed by (searchText, offset), and details
    by path. Records every search body."""

    def __init__(
        self,
        pages: dict[tuple[str, int], dict[str, Any]],
        details: dict[str, dict[str, Any] | Exception],
        allowed: bool = True,
    ) -> None:
        self.pages = pages
        self.details = details
        self.is_allowed = allowed
        self.searches: list[dict[str, Any]] = []
        self.detail_calls: list[str] = []

    async def allowed(self, url: str) -> bool:
        return self.is_allowed

    async def post_json(self, url: str, body: dict[str, Any]) -> dict[str, Any]:
        self.searches.append(body)
        if body["searchText"] == "":
            return {"total": 2000, "jobPostings": [], "facets": FACETS}
        return self.pages.get((body["searchText"], body["offset"]), {"total": 0, "jobPostings": []})

    async def get_json(self, url: str) -> dict[str, Any]:
        path = url.removeprefix(API)
        self.detail_calls.append(path)
        answer = self.details[path]
        if isinstance(answer, Exception):
            raise answer
        return answer


async def nothing_stored(url: str) -> bool:
    return False


FILTERS = Filters(titles=["LLM"], locations=["India"], workdayMaxPages=5)


async def test_the_country_facet_is_found_nested_and_applied() -> None:
    http = FakeFetcher({}, {})
    await workday.fetch(SOURCE, http, nothing_stored, FILTERS)
    keyword_searches = [s for s in http.searches if s["searchText"]]
    assert keyword_searches[0]["appliedFacets"] == {"locationCountry": [INDIA]}


async def test_paging_stops_at_the_first_page_with_nothing_wanted() -> None:
    http = FakeFetcher(
        {
            ("LLM", 0): {
                "total": 2000,
                "jobPostings": [listing("LLM Model Developer", "/job/Pune/a1")]
                + [listing("Java Developer", f"/job/Pune/x{i}") for i in range(19)],
            },
            # Later pages report 0 — the real total is only on the first.
            ("LLM", 20): {"total": 0, "jobPostings": [listing("SAP Consultant", "/job/Pune/s1")]},
            ("LLM", 40): {"total": 0, "jobPostings": [listing("LLM Engineer", "/job/Pune/never")]},
        },
        {"/job/Pune/a1": detail("LLM Model Developer", "/job/Pune/a1")},
    )
    harvest = await workday.fetch(SOURCE, http, nothing_stored, FILTERS)

    offsets = [s["offset"] for s in http.searches if s["searchText"] == "LLM"]
    assert offsets == [0, 20]
    assert http.detail_calls == ["/job/Pune/a1"]
    assert harvest.fetched == 21
    assert [p.title for p in harvest.postings] == ["LLM Model Developer"]


async def test_a_posting_outside_the_wanted_country_is_dropped() -> None:
    http = FakeFetcher(
        {
            ("LLM", 0): {
                "total": 2,
                "jobPostings": [
                    listing("LLM Engineer", "/job/Pune/in1"),
                    listing("LLM Engineer", "/job/Bratislava/sk1"),
                ],
            }
        },
        {
            "/job/Pune/in1": detail("LLM Engineer", "/job/Pune/in1"),
            "/job/Bratislava/sk1": detail(
                "LLM Engineer",
                "/job/Bratislava/sk1",
                location="Bratislava",
                country={"descriptor": "Slovakia", "id": "sk"},
            ),
        },
    )
    harvest = await workday.fetch(SOURCE, http, nothing_stored, FILTERS)
    assert [p.location for p in harvest.postings] == ["Hyderabad, India"]


async def test_fields_come_from_the_board() -> None:
    path = "/job/Hyderabad/AI---ML-Engineer_ATCI-5482962-S2002430-1"
    http = FakeFetcher(
        {("LLM", 0): {"total": 1, "jobPostings": [listing("LLM Engineer", path)]}},
        {
            path: detail(
                "LLM Engineer",
                path,
                jobReqId="ATCI-5482962-S2002430",
                additionalLocations=["Bengaluru"],
                remoteType="Hybrid",
            )
        },
    )
    posting = (await workday.fetch(SOURCE, http, nothing_stored, FILTERS)).postings[0]

    assert posting.refId == "ATCI-5482962-S2002430"
    assert posting.company == "Accenture"
    assert posting.location == "Hyderabad; Bengaluru, India"
    assert posting.country == "India"
    assert posting.jobType == "full_time"
    assert posting.workMode == "hybrid"
    assert (
        posting.postedAt is not None and posting.postedAt.isoformat() == "2026-09-24T00:00:00+00:00"
    )
    assert posting.listingUrl.endswith(path)


async def test_a_disallowed_site_is_refused_before_any_search() -> None:
    http = FakeFetcher({}, {}, allowed=False)
    with pytest.raises(RobotsDisallowed):
        await workday.fetch(SOURCE, http, nothing_stored, FILTERS)
    assert http.searches == []


async def test_a_failed_detail_is_counted_not_fatal() -> None:
    http = FakeFetcher(
        {
            ("LLM", 0): {
                "total": 2,
                "jobPostings": [
                    listing("LLM Engineer", "/job/Pune/ok"),
                    listing("LLM Lead", "/job/Pune/bad"),
                ],
            }
        },
        {
            "/job/Pune/ok": detail("LLM Engineer", "/job/Pune/ok"),
            "/job/Pune/bad": ValueError("boom"),
        },
    )
    harvest = await workday.fetch(SOURCE, http, nothing_stored, FILTERS)
    assert harvest.failed == 1
    assert [p.title for p in harvest.postings] == ["LLM Engineer"]


async def test_a_stored_posting_is_not_fetched_again() -> None:
    stored_path = "/job/Pune/old"
    http = FakeFetcher(
        {
            ("LLM", 0): {
                "total": 2,
                "jobPostings": [
                    listing("LLM Engineer", stored_path),
                    listing("LLM Lead", "/job/Pune/new"),
                ],
            }
        },
        {"/job/Pune/new": detail("LLM Lead", "/job/Pune/new")},
    )
    asked: list[str] = []

    async def is_stored(url: str) -> bool:
        asked.append(url)
        return url.endswith(stored_path)

    harvest = await workday.fetch(SOURCE, http, is_stored, FILTERS)

    # The URL asked about is the one ingest stores as `listingUrl`.
    assert f"https://accenture.wd103.myworkdayjobs.com/AccentureCareers{stored_path}" in asked
    assert http.detail_calls == ["/job/Pune/new"]
    assert harvest.known == 1
    assert [p.title for p in harvest.postings] == ["LLM Lead"]


async def test_the_page_cap_comes_from_the_run() -> None:
    page = {
        "total": 2000,
        "jobPostings": [listing("LLM Engineer", f"/job/Pune/p{i}") for i in range(20)],
    }
    http = FakeFetcher({("LLM", offset): page for offset in range(0, 200, 20)}, {})
    http.details = {
        row["externalPath"]: detail("LLM Engineer", row["externalPath"])
        for row in page["jobPostings"]
    }

    await workday.fetch(
        SOURCE, http, nothing_stored, FILTERS.model_copy(update={"workdayMaxPages": 2})
    )
    assert [s["offset"] for s in http.searches if s["searchText"] == "LLM"] == [0, 20]


async def test_every_saved_title_is_searched() -> None:
    http = FakeFetcher({}, {})
    two = FILTERS.model_copy(update={"titles": ["LLM", "GenAI"]})
    await workday.fetch(SOURCE, http, nothing_stored, two)
    assert [s["searchText"] for s in http.searches if s["searchText"]] == ["LLM", "GenAI"]


async def test_no_more_details_are_fetched_than_the_run_can_take() -> None:
    """A run limited to 2 new jobs downloads 2 details, not every new posting."""
    paths = [f"/job/Pune/a{n}" for n in range(5)]
    http = FakeFetcher(
        {("LLM", 0): {"total": 5, "jobPostings": [listing("LLM Engineer", p) for p in paths]}},
        {p: detail("LLM Engineer", p) for p in paths},
    )

    harvest = await workday.fetch(SOURCE, http, nothing_stored, FILTERS, limit=2)

    assert len(http.detail_calls) == 2
    assert len(harvest.postings) == 2
