"""Repeating blocks in a template's own LaTeX.

`{{EXPERIENCE}}` hands the whole section to a Python builder, so a template picks
between the shapes `latex.py` knows how to emit. A loop block instead lets the `.tex`
say what one row looks like and have it repeated:

    {{#WORK}}
    \\jobtitle{{{.title}}}{{{.company}}}{{{.dates}}}{{{.location}}}
    {{#.bullets}}  \\item {{.}}
    {{/.bullets}}{{/WORK}}

Both forms work, and a template may mix them — the skills grid is easier as
`{{SKILLS}}`, whose column chunking has no natural spelling in a loop.

Every substituted value is escaped on the way in, so a template cannot forget to.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

from modules.profile.models import UserProfile
from modules.template.latex import tex
from modules.template.models import LocationStyle, TemplateStyle

# `{{#NAME}}` opens a top-level collection, `{{#.field}}` a list on the current item.
# `{{?...}}` takes the same names and renders its body *once*, and only if the list has
# anything in it — which is how `\begin{itemize}` gets written without a bare one being
# emitted for a role that has no bullets. LaTeX treats that as an error, not as nothing.
_OPEN = re.compile(r"\{\{([#?])([A-Z_]+|\.[A-Za-z_]+)\}\}")
# `{{.field}}` is a field of the current item; `{{.}}` the item itself, for a list
# of plain strings.
_FIELD = re.compile(r"\{\{(\.[A-Za-z_]*)\}\}")

# What a section may loop over, and the fields one of its items offers. A field
# holding a list is also what a nested `{{#.field}}` names.
COLLECTIONS: dict[str, frozenset[str]] = {
    "WORK": frozenset(
        {".title", ".company", ".location", ".start", ".end", ".dates", ".bullets", ".projects"}
    ),
    "EDUCATION": frozenset(
        {".degree", ".institution", ".location", ".where", ".start", ".end", ".dates"}
    ),
    "SKILLS": frozenset({".name", ".items", ".joined"}),
    "CERTIFICATIONS": frozenset({".name", ".issuer", ".year"}),
}

# Nested lists, by the field that holds them: the fields their own items offer.
# `.` alone means a list of plain strings, written `{{.}}`.
NESTED: dict[str, frozenset[str]] = {
    ".bullets": frozenset({"."}),
    ".items": frozenset({"."}),
    ".projects": frozenset({".name", ".bullets"}),
}


class BlockError(Exception):
    """The template's loop blocks do not parse. Carries the message the uploader sees."""


def has_blocks(source: str) -> bool:
    return _OPEN.search(source) is not None


def _dates(start: str | None, end: str | None, current: bool = False) -> str:
    finish = "Present" if current else (end or "")
    if start and finish:
        return f"{start} -- {finish}"
    return start or finish or ""


def _place(value: str | None, style: LocationStyle) -> str:
    if not value:
        return ""
    return value.split(",")[0].strip() if style is LocationStyle.CITY else value


def context_for(resume: UserProfile, style: TemplateStyle) -> dict[str, list[dict[str, Any]]]:
    """The profile as plain values, shaped the way the template names them.

    Values stay raw — escaping happens once, where a field is substituted.
    """
    return {
        "WORK": [
            {
                ".title": role.title,
                ".company": role.company,
                ".location": _place(role.location, style.location),
                ".start": role.start,
                ".end": role.end or "",
                ".dates": _dates(role.start, role.end, role.current),
                ".bullets": list(role.bullets),
                ".projects": [
                    {".name": project.name, ".bullets": list(project.bullets)}
                    for project in role.projects
                ],
            }
            for role in resume.work
        ],
        "EDUCATION": [
            {
                ".degree": entry.degree,
                ".institution": entry.institution,
                ".location": entry.location or "",
                ".where": ", ".join(p for p in (entry.institution, entry.location) if p),
                ".start": entry.start or "",
                ".end": entry.end or "",
                ".dates": _dates(entry.start, entry.end),
            }
            for entry in resume.education
        ],
        "SKILLS": [
            {".name": group.name, ".items": list(group.items), ".joined": ", ".join(group.items)}
            for group in resume.skill
        ],
        "CERTIFICATIONS": [
            {".name": entry.name, ".issuer": entry.issuer, ".year": entry.year or ""}
            for entry in resume.certification
        ],
    }


def _body(source: str, start: int, name: str) -> tuple[str, int]:
    """The text between `{{#name}}` and its own `{{/name}}`, and where to resume.

    Depth is counted so a `.bullets` list inside `.projects` closes against the right
    tag when the outer item also has one.
    """
    close = f"{{{{/{name}}}}}"
    opens = (f"{{{{#{name}}}}}", f"{{{{?{name}}}}}")
    depth, cursor = 1, start
    while depth:
        next_close = source.find(close, cursor)
        if next_close == -1:
            raise BlockError(f"{{{{#{name}}}}} is never closed")
        found = [(source.find(tag, cursor), tag) for tag in opens]
        nearest = min(((at, tag) for at, tag in found if at != -1), default=None)
        if nearest is not None and nearest[0] < next_close:
            depth += 1
            cursor = nearest[0] + len(nearest[1])
        else:
            depth -= 1
            cursor = next_close + len(close)
    return source[start : cursor - len(close)], cursor


def _fields(text: str, item: Any) -> str:
    def value(match: re.Match[str]) -> str:
        key = match.group(1)
        if key == ".":
            return tex(str(item))
        found = item.get(key, "") if isinstance(item, dict) else ""
        return tex(", ".join(found) if isinstance(found, list) else str(found))

    return _FIELD.sub(value, text)


def expand(source: str, item: Any, root: dict[str, Any]) -> str:
    """Replace every loop block in `source`, then every field, against `item`."""
    out: list[str] = []
    cursor = 0
    while True:
        opening = _OPEN.search(source, cursor)
        if opening is None:
            out.append(_fields(source[cursor:], item))
            return "".join(out)

        out.append(_fields(source[cursor : opening.start()], item))
        sigil, name = opening.groups()
        body, cursor = _body(source, opening.end(), name)

        rows = root.get(name, []) if name in COLLECTIONS else _sequence(item, name)
        if sigil == "?":
            # Once, against the item we are already on — the list is only the condition.
            out.append(expand(body, item, root) if rows else "")
        else:
            out.append("".join(expand(body, row, root) for row in rows))


def _sequence(item: Any, name: str) -> Sequence[Any]:
    found = item.get(name) if isinstance(item, dict) else None
    return found if isinstance(found, list) else []


def render_blocks(source: str, resume: UserProfile, style: TemplateStyle) -> str:
    root = context_for(resume, style)
    return expand(source, root, root)


def validate(source: str) -> None:
    """Reject a template whose blocks are unbalanced, or whose fields do not exist.

    An unknown field would otherwise render as nothing at all, which looks like a
    missing profile rather than a typo in the template.
    """
    _walk(source, available=frozenset(), inside=None)


def _walk(source: str, available: frozenset[str], inside: str | None) -> None:
    cursor = 0
    while True:
        opening = _OPEN.search(source, cursor)
        if opening is None:
            _check_fields(source[cursor:], available, inside)
            return

        _check_fields(source[cursor : opening.start()], available, inside)
        sigil, name = opening.groups()

        if name in COLLECTIONS:
            if inside is not None:
                raise BlockError(f"{{{{#{name}}}}} cannot be nested inside {{{{#{inside}}}}}")
            fields = COLLECTIONS[name]
        elif name in NESTED:
            if name not in available:
                where = f"an item of {{{{#{inside}}}}}" if inside else "the document"
                raise BlockError(f"{{{{#{name}}}}} is not a list on {where}")
            fields = NESTED[name]
        else:
            raise BlockError(
                f"unknown block {{{{#{name}}}}} — available: "
                + ", ".join("{{#" + key + "}}" for key in sorted(COLLECTIONS))
            )

        body, cursor = _body(source, opening.end(), name)
        # `{{?...}}` does not descend: its body still names the enclosing item's fields.
        _walk(body, available if sigil == "?" else fields, inside if sigil == "?" else name)


def _check_fields(text: str, available: frozenset[str], inside: str | None) -> None:
    for match in _FIELD.finditer(text):
        key = match.group(1)
        if inside is None:
            raise BlockError(f"{{{{{key}}}}} is outside every block, so it names nothing")
        if key not in available:
            raise BlockError(
                f"{{{{{key}}}}} is not a field of {{{{#{inside}}}}} — available: "
                + ", ".join("{{" + field + "}}" for field in sorted(available))
            )
