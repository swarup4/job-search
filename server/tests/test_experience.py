"""P3-33 — an experience range as numbers, parsed from the posting's own words.

The first group is pure and needs no database. The last two tests check that the
numbers are written with the band, and those need the MongoDB the rest of the suite
uses.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from modules.job.experience import parse_experience


@pytest.mark.parametrize(
    ("band", "expected"),
    [
        ("11-15 years", (11, 15)),
        ("6 - 10 Years", (6, 10)),
        ("6–10 years", (6, 10)),
        ("3 to 5 yrs", (3, 5)),
        ("0-1 years", (0, 1)),
        ("5+ years", (5, None)),
        ("5 + years of experience", (5, None)),
        ("Minimum 8 years of experience", (8, None)),
        ("At least 12 years", (12, None)),
        ("8 years", (8, None)),
        ("1 year", (1, None)),
        ("10+ yrs", (10, None)),
        ("4.5 years", (4, None)),
        ("up to 3 years", (0, 3)),
        ("Less than 2 years", (0, 2)),
        ("Fresher", (0, 0)),
        ("Entry-level", (0, 0)),
    ],
)
def test_a_band_that_states_figures_is_read(band: str, expected: tuple[int, int | None]) -> None:
    assert parse_experience(band) == expected


@pytest.mark.parametrize(
    "band",
    [
        None,
        "",
        "   ",
        "Senior level",
        "Experienced professional",
        # No unit: a number alone could be anything.
        "8",
        "Grade 7",
        # Not ranges anyone meant, and not years.
        "10-5 years",
        "99 years",
        "2019-2024",
    ],
)
def test_a_band_that_states_no_figure_reads_as_nothing(band: str | None) -> None:
    """A parser that answers None cannot invent a year."""
    assert parse_experience(band) == (None, None)


def test_a_range_wins_over_a_lone_figure_beside_it() -> None:
    assert parse_experience("6-10 years (8 years preferred)") == (6, 10)


# --- written with the band --------------------------------------------------------


async def test_a_job_created_with_a_band_carries_its_numbers(signed_in: AsyncClient) -> None:
    created = await signed_in.post(
        "/job/createJob",
        json={
            "title": "LLM Engineer",
            "company": "Acme",
            "location": "Bengaluru, India",
            "source": "career_page",
            "refId": "R1",
            "experienceBand": "11-15 years",
        },
    )
    assert created.status_code == 201, created.text

    job = (await signed_in.get(f"/job/getJob/{created.json()['id']}")).json()
    assert (job["experienceMin"], job["experienceMax"]) == (11, 15)


async def test_a_band_written_later_brings_its_numbers_with_it(signed_in: AsyncClient) -> None:
    """Analysis fills the band after the job exists. The numbers follow the text."""
    created = await signed_in.post(
        "/job/createJob",
        json={
            "title": "LLM Engineer",
            "company": "Acme",
            "location": "Bengaluru, India",
            "source": "career_page",
            "refId": "R2",
        },
    )
    job_id = created.json()["id"]
    assert (await signed_in.get(f"/job/getJob/{job_id}")).json()["experienceMin"] is None

    updated = await signed_in.patch(
        f"/job/updateJob/{job_id}", json={"experienceBand": "Minimum 8 years of experience"}
    )
    assert updated.status_code == 200, updated.text

    job = (await signed_in.get(f"/job/getJob/{job_id}")).json()
    assert (job["experienceMin"], job["experienceMax"]) == (8, None)
