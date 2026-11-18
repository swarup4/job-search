"""Pass/fail checks on a posting, made in code before any model compares it. (CE-12)

A posting in the wrong country, in a work mode the user ruled out, or pitched below the
experience they are looking for is not worth a comparison call — and the answer is not
a judgement, so a model has no business making it. Each gate compares what the posting
*states* with the user's saved Search targets:

| gate       | posting                              | fails when                          |
|------------|--------------------------------------|-------------------------------------|
| location   | its location, country and cities     | its country is known and it names   |
|            |                                      | none of your locations              |
| work mode  | the mode the brief or the board gave | it differs from the one you saved   |
| experience | the brief's minimum years            | it is below your minimum            |

Silence passes. A posting that does not say where it is, how it works or how many
years it wants is compared as before: a gate may only fail a posting on something the
posting said, never on something it left out.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from agents.evidence import flatten, occurrences

MODE_NAMES = {"on_site": "on-site", "hybrid": "hybrid", "remote": "remote"}


class Constraints(Protocol):
    """The part of a brief the gates read."""

    minYears: int | None
    workMode: str | None


@dataclass(frozen=True)
class Gate:
    """Why a posting was not compared. Shown to the user as the match's one risk."""

    key: str
    title: str
    detail: str


def check_gates(
    brief: Constraints, job: dict[str, Any], preferences: dict[str, Any] | None
) -> Gate | None:
    """The first gate the posting fails, or None when it passes them all."""
    preferences = preferences or {}
    return (
        _location(job, preferences.get("locations") or [])
        or _work_mode(brief.workMode or job.get("workMode"), preferences.get("workMode"))
        or _experience(brief.minYears, preferences.get("minExperience"))
    )


def _location(job: dict[str, Any], wanted: list[str]) -> Gate | None:
    place = ", ".join(
        part
        for part in [job.get("location") or "", job.get("country") or "", *job.get("cities", [])]
        if part
    )
    flat = flatten(place)
    # A posting whose country could not be read is not failed on its city alone: a
    # search target of "India" says nothing about a bare "Whitefield".
    if not flat or not wanted or not job.get("country"):
        return None
    if any(occurrences(term, flat) for term in wanted if term.strip()):
        return None
    return Gate(
        key="gate-location",
        title="Outside your locations",
        detail=(
            f"The posting is in {(job.get('location') or place)[:80]}; your search targets "
            f"are {', '.join(wanted)[:120]}. It was not compared with your profile."
        ),
    )


def _work_mode(stated: str | None, wanted: str | None) -> Gate | None:
    if not stated or not wanted or stated == wanted:
        return None
    return Gate(
        key="gate-work-mode",
        title="Not your work mode",
        detail=(
            f"The posting is {MODE_NAMES.get(stated, stated)}; your search targets ask for "
            f"{MODE_NAMES.get(wanted, wanted)}. It was not compared with your profile."
        ),
    )


def _experience(stated: int | None, wanted: int | None) -> Gate | None:
    if stated is None or wanted is None or stated >= wanted:
        return None
    return Gate(
        key="gate-experience",
        title="Below your experience level",
        detail=(
            f"The posting asks for {stated}+ years; your search targets start at {wanted}. "
            "It was not compared with your profile."
        ),
    )


if __name__ == "__main__":
    from types import SimpleNamespace

    print(
        check_gates(
            SimpleNamespace(minYears=2, workMode="remote"),
            {"location": "Austin, TX", "country": "United States", "cities": ["Austin"]},
            {"locations": ["India"], "workMode": "hybrid", "minExperience": 8},
        )
    )
