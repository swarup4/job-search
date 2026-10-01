"""The checks that keep a model honest, and the profile text they check against.

Every agent that lets a model quote a source verifies the quote here before using it:
a span is accepted only if it really appears in the text it claims to come from.
"""

from __future__ import annotations

import re
from typing import Any

_WORD_RE = re.compile(r"[^a-z0-9]+")


def slug(value: str) -> str:
    return _WORD_RE.sub("-", value.strip().lower()).strip("-")


def flatten(value: str) -> str:
    """Lowercased, whitespace-collapsed, so a quote that differs only in line breaks
    still matches the source it was copied from."""
    return re.sub(r"\s+", " ", value).strip().lower()


def occurrences(needle: str, flat_haystack: str) -> int:
    pattern = re.escape(flatten(needle))
    return len(re.findall(rf"(?<![a-z0-9]){pattern}(?![a-z0-9])", flat_haystack))


def verified_span(span: str, flat_source: str) -> str | None:
    """The span, if it really was copied from the source."""
    cleaned = re.sub(r"\s+", " ", span).strip()
    if len(cleaned) < 8:
        return None
    return cleaned if flatten(cleaned) in flat_source else None


def sentence_with(label: str, source: str) -> str | None:
    """The source's own sentence naming the label — the fallback when the model's quote
    cannot be found but the label itself can."""
    flat_label = flatten(label)
    for sentence in re.split(r"(?<=[.!?\n])\s+", source):
        cleaned = re.sub(r"\s+", " ", sentence).strip()
        if flat_label and flat_label in flatten(cleaned):
            return cleaned[:300]
    return None


def profile_corpus(profile: dict[str, Any]) -> str:
    """Everything a comparison may weigh — every role, not just the current one."""
    personal = profile.get("profile") or {}
    parts: list[str] = [
        f"Name: {profile.get('name', '')}",
        f"Current role: {profile.get('role', '')}",
    ]
    if personal.get("headline"):
        parts.append(f"Headline: {personal['headline']}")
    if personal.get("summary"):
        parts.append(f"Summary: {personal['summary']}")

    for entry in profile.get("work", []):
        until = "Present" if entry.get("current") else (entry.get("end") or "")
        parts.append(
            f"\n{entry.get('title', '')} — {entry.get('company', '')} ({entry.get('start', '')} to {until})"
        )
        parts.extend(f"  - {bullet}" for bullet in entry.get("bullets", []))
        for project in entry.get("projects", []):
            parts.append(f"  Project: {project.get('name', '')}")
            parts.extend(f"    - {bullet}" for bullet in project.get("bullets", []))

    groups = profile.get("skill", [])
    if groups:
        parts.append("\nSkills")
        parts.extend(
            f"  {group.get('name', '')}: {', '.join(group.get('items', []))}" for group in groups
        )

    education = profile.get("education", [])
    if education:
        parts.append("\nEducation")
        parts.extend(
            f"  {entry.get('degree', '')}, {entry.get('institution', '')}" for entry in education
        )

    certifications = profile.get("certification", [])
    if certifications:
        parts.append("\nCertifications")
        parts.extend(
            f"  {entry.get('name', '')} — {entry.get('issuer', '')}" for entry in certifications
        )

    return "\n".join(parts)


def profile_digest(profile: dict[str, Any]) -> str:
    """The shorter view the risk check works from: who they are and how long, not
    every bullet they have ever written."""
    personal = profile.get("profile") or {}
    work = profile.get("work", [])
    lines = [
        f"Role: {profile.get('role', '')}",
        f"Headline: {personal.get('headline', '')}",
        f"Location: {personal.get('location', '')}",
        f"Roles held: {len(work)}",
    ]
    lines.extend(
        f"  {entry.get('title', '')} at {entry.get('company', '')} "
        f"({entry.get('start', '')} to {'Present' if entry.get('current') else entry.get('end') or ''})"
        for entry in work
    )
    lines.append(
        "Skills: "
        + "; ".join(
            f"{group.get('name', '')}: {', '.join(group.get('items', []))}"
            for group in profile.get("skill", [])
        )
    )
    lines.extend(
        f"Education: {entry.get('degree', '')}, {entry.get('institution', '')}"
        for entry in profile.get("education", [])
    )
    return "\n".join(lines)
