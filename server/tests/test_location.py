"""P3-31 — country and cities from a board's `location`. Every sample is a real
spelling from the stored jobs, which is the point: the parser is only as good as the
worst text it has been shown."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from modules.job.location import canonical_country, parse_location


@pytest.mark.parametrize(
    ("location", "country", "cities"),
    [
        ("Bengaluru, India", "India", ["Bengaluru"]),
        ("Bangalore,IND, India", "India", ["Bengaluru"]),
        ("IN - Bengaluru, India", "India", ["Bengaluru"]),
        ("India - Bangalore", "India", ["Bengaluru"]),
        ("India, Bangalore", "India", ["Bengaluru"]),
        ("Bangalore Area, India", "India", ["Bengaluru"]),
        ("Bengaluru, BDC9A, India", "India", ["Bengaluru"]),
        ("IND - KA - BANGALORE, India", "India", ["Bengaluru"]),
        ("IND.Pune, India", "India", ["Pune"]),
        ("Pune - Business Bay, India", "India", ["Pune"]),
        ("1401-GIPL: Prestige Technology Park IV, Bangalore, India", "India", ["Bengaluru"]),
        ("1401-G-India: DLF Commercial Building 3, Phase V, Gurugram", "India", ["Gurugram"]),
        ("1401-G-India: ITES SEZ Building No. 7, Sector-135 Noida", "India", ["Noida"]),
        (
            (
                "IN-KA-BENGALURU-NORTHGATE ~ Sy No 2/2 Venkatala Village ~ SY NO 2/2 "
                "VENKATALA VILLAGE, Yelahanka Hobli, India"
            ),
            "India",
            ["Bengaluru"],
        ),
        (
            (
                "Tower 02, Manyata Embassy Business Park, Racenahali & Nagawara Villages. "
                "Outer Ring Rd, Bangalore 540065, India"
            ),
            "India",
            ["Bengaluru"],
        ),
        ("Gurgaon, Haryana, India", "India", ["Gurugram"]),
        ("Greater Noida, Uttar Pradesh, India", "India", ["Greater Noida"]),
        ("India - Gurgaon; India - Hyderabad", "India", ["Gurugram", "Hyderabad"]),
        ("Bengaluru; Mumbai; Chennai; Hyderabad, India", "India",
         ["Bengaluru", "Mumbai", "Chennai", "Hyderabad"]),
    ],
)  # fmt: skip
def test_real_spellings(location: str, country: str, cities: list[str]) -> None:
    assert parse_location(location) == (country, cities)


def test_a_building_name_is_not_a_city() -> None:
    assert parse_location("Mumbai, Maharashtra, India; RMZ TITANIUM") == ("India", ["Mumbai"])


def test_a_region_alone_gives_no_city() -> None:
    assert parse_location("Tamil Nadu, India") == ("India", [])
    assert parse_location("Virtual Office (Telangana), India") == ("India", [])


def test_the_primary_country_is_the_one_named_last() -> None:
    """A posting across two countries keeps every city, but has one country."""
    country, cities = parse_location(
        "Bengaluru, Karnātaka, India; Bucharest, Ilfov, Romania; Chennai, Tamil Nadu, India"
    )

    assert country == "India"
    assert cities == ["Bengaluru", "Bucharest", "Chennai"]


def test_cities_outside_india_come_from_a_plain_city_region_pair() -> None:
    assert parse_location(
        "Seattle, Washington, US; Austin, Texas, US, United States of America"
    ) == (
        "United States",
        ["Seattle", "Austin"],
    )


@pytest.mark.parametrize(
    ("location", "country"),
    [
        ("Auckland, New Zealand", "New Zealand"),
        ("Copenhagen, Denmark", "Denmark"),
        ("Helsinki, Finland", "Finland"),
        ("Auckland, NZ", "New Zealand"),
        ("Copenhagen, DNK", "Denmark"),
        ("Hanoi, Viet Nam", "Vietnam"),
        ("Seoul, Korea, Republic of", "South Korea"),
        ("Moscow, Russian Federation", "Russia"),
        ("Port Moresby, Papua New Guinea", "Papua New Guinea"),
        ("London, England", "United Kingdom"),
    ],
)
def test_every_iso_country_is_known(location: str, country: str) -> None:
    assert parse_location(location)[0] == country


def test_a_us_state_that_shares_a_countrys_name_is_not_a_country() -> None:
    assert parse_location("Atlanta, Georgia") == (None, ["Atlanta"])
    assert parse_location("Newark, New Jersey") == (None, ["Newark"])


def test_an_office_code_is_not_a_country_code() -> None:
    """`BDC9A`, `TSA`, `SEZ` sit in comma parts too; only a bare capital code counts."""
    assert parse_location("Bengaluru, Maruthi Onyx - TESCO TSA, India") == ("India", ["Bengaluru"])


def test_nothing_named_is_nothing_stored() -> None:
    assert parse_location("") == (None, [])
    assert parse_location("Somewhere Else") == (None, [])


def test_a_boards_country_keeps_its_value_in_the_common_spelling() -> None:
    assert canonical_country("United States of America") == "United States"
    assert canonical_country("Atlantis") == "Atlantis"
    assert canonical_country("  ") is None


# --- written on create -------------------------------------------------------


def job(**overrides: object) -> dict[str, object]:
    return {
        "title": "GenAI Engineer",
        "company": "Visa",
        "location": "Bangalore,IND, India",
        "source": "career_page",
        "refId": "R1",
        **overrides,
    }


async def test_a_new_job_is_given_its_country_and_cities(signed_in: AsyncClient) -> None:
    created = (await signed_in.post("/job/createJob", json=job())).json()

    read = (await signed_in.get(f"/job/getJob/{created['id']}")).json()

    assert (read["country"], read["cities"]) == ("India", ["Bengaluru"])


async def test_the_boards_own_country_wins_over_the_text(signed_in: AsyncClient) -> None:
    created = (
        await signed_in.post(
            "/job/createJob",
            json=job(
                location="Boston, Massachusetts; Bangalore", country="United States of America"
            ),
        )
    ).json()

    read = (await signed_in.get(f"/job/getJob/{created['id']}")).json()

    assert read["country"] == "United States"
    assert read["cities"] == ["Boston", "Bengaluru"]
