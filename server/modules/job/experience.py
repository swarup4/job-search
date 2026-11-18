"""P3-33 — a posting's experience range as numbers, read from its own words.

`experienceBand` is the posting's text, kept verbatim ("11-15 years", "Minimum 8 years
of experience"). A filter cannot compare text, so the range is parsed out of it here —
parsed, not generated: the band already holds the numbers, and a parser that answers
`None` cannot invent a year.

| band                               | min | max  |
|------------------------------------|-----|------|
| "11-15 years", "6 to 10 yrs"       | 11  | 15   |
| "5+ years", "Minimum 8 years"      | 5   | None |
| "8 years of experience"            | 8   | None |
| "up to 3 years", "less than 2 yrs" | 0   | 3    |
| "Fresher", "0-1 years"             | 0   | 0/1  |
| "Senior level", ""                 | None| None |

A lone figure is a minimum: a posting that says "8 years" means at least eight.
"""

from __future__ import annotations

import re

# A career is not longer than this; a bigger number in the band is a year, a salary or
# a requisition id that strayed into it.
MAX_YEARS = 50

_NUMBER = r"(\d{1,2})(?:\.\d)?"
_UNIT = r"\s*\+?\s*(?:years?|yrs?|yoe)\b"
_RANGE = re.compile(rf"{_NUMBER}\s*(?:-|–|—|to)\s*{_NUMBER}{_UNIT}", re.IGNORECASE)
_AT_MOST = re.compile(
    rf"(?:up\s*to|upto|less than|under|below|at most|maximum(?: of)?|max\.?)\s*{_NUMBER}{_UNIT}",
    re.IGNORECASE,
)
_SINGLE = re.compile(rf"{_NUMBER}{_UNIT}", re.IGNORECASE)
_FRESHER = re.compile(r"\b(?:freshers?|no experience|entry[- ]level)\b", re.IGNORECASE)


def parse_experience(band: str | None) -> tuple[int | None, int | None]:
    """`(min, max)` years. Either may be None; both are when the band states no figure."""
    text = (band or "").strip()
    if not text:
        return None, None

    span = _RANGE.search(text)
    if span:
        low, high = int(span.group(1)), int(span.group(2))
        # "10-5 years" is not a range anyone meant; read nothing rather than guess.
        return (low, high) if low <= high <= MAX_YEARS else (None, None)

    ceiling = _AT_MOST.search(text)
    if ceiling:
        high = int(ceiling.group(1))
        return (0, high) if high <= MAX_YEARS else (None, None)

    single = _SINGLE.search(text)
    if single:
        low = int(single.group(1))
        return (low, None) if low <= MAX_YEARS else (None, None)

    if _FRESHER.search(text):
        return 0, 0
    return None, None
