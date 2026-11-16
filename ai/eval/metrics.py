"""The arithmetic of an evaluation. Pure functions over labels and answers.

Labels are compared as slugs, so "Node.js" and "node js" are one requirement and a
difference in case or punctuation is not scored as a miss.

The number that matters most is `wrong_present`: a requirement reported Present that
the profile does not show. It is the harmful direction — it hides a keyword the user
would otherwise have been offered — so it is reported on its own, not folded into
accuracy.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from agents.details import DETAIL_FIELDS, JobDetails
from agents.evidence import slug


@dataclass(frozen=True)
class Counts:
    """Tallies that can be summed across postings before any rate is taken — a mean of
    per-posting rates would let a three-requirement posting outvote a twenty-one."""

    # Requirements: what the brief found against what the posting states.
    required: int = 0
    found: int = 0
    found_right: int = 0
    # Details: of the four, how many came back exactly as labelled.
    details: int = 0
    details_right: int = 0
    # Verdicts: of the labelled requirements the pipeline judged.
    judged: int = 0
    judged_right: int = 0
    labelled_missing: int = 0
    wrong_present: int = 0
    labelled_present: int = 0
    wrong_missing: int = 0

    def __add__(self, other: Counts) -> Counts:
        return Counts(*(a + b for a, b in zip(asdict(self).values(), asdict(other).values())))


def _rate(part: int, whole: int) -> float | None:
    """None, not zero, when there was nothing to measure: "no labelled-missing
    requirements" must not read as "never wrong about one"."""
    return round(part / whole, 4) if whole else None


def rates(counts: Counts) -> dict[str, float | None]:
    return {
        "requirementPrecision": _rate(counts.found_right, counts.found),
        "requirementRecall": _rate(counts.found_right, counts.required),
        "detailAccuracy": _rate(counts.details_right, counts.details),
        "verdictAccuracy": _rate(counts.judged_right, counts.judged),
        # Of the requirements the profile does not show, how many were called Present.
        "wrongPresentRate": _rate(counts.wrong_present, counts.labelled_missing),
        # Of the ones it does show, how many were called Missing — the safe direction.
        "wrongMissingRate": _rate(counts.wrong_missing, counts.labelled_present),
    }


def requirement_counts(expected: list[str], found: list[str]) -> Counts:
    wanted = {slug(label) for label in expected} - {""}
    got = {slug(label) for label in found} - {""}
    return Counts(required=len(wanted), found=len(got), found_right=len(wanted & got))


def detail_counts(expected: JobDetails, found: JobDetails) -> Counts:
    """Exact after normalising whitespace and case. A detail the posting does not state
    is right only when the pipeline also reports nothing."""
    right = sum(
        _same(getattr(expected, name), getattr(found, name))
        for name in ("experience", "salary", "workMode", "jobType")
    )
    return Counts(details=len(DETAIL_FIELDS), details_right=right)


def _same(expected: str | None, found: str | None) -> bool:
    return " ".join((expected or "").lower().split()) == " ".join((found or "").lower().split())


def verdict_counts(
    expected_present: list[str],
    expected_missing: list[str],
    got_present: list[str],
    got_missing: list[str],
) -> Counts:
    """Only requirements that are both labelled and judged are scored. One the brief
    never extracted is a recall miss, counted there, not a wrong verdict here."""
    want_present = {slug(label) for label in expected_present}
    want_missing = {slug(label) for label in expected_missing}
    said_present = {slug(label) for label in got_present}
    said_missing = {slug(label) for label in got_missing}
    judged = said_present | said_missing

    wrong_present = len(want_missing & said_present)
    wrong_missing = len(want_present & said_missing)
    scored = len((want_present | want_missing) & judged)
    return Counts(
        judged=scored,
        judged_right=scored - wrong_present - wrong_missing,
        labelled_missing=len(want_missing & judged),
        wrong_present=wrong_present,
        labelled_present=len(want_present & judged),
        wrong_missing=wrong_missing,
    )
