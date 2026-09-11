"""Profile data to LaTeX fragments. Pure functions — no I/O, no database, no file paths.

Each builder emits the block that replaces one `{{TOKEN}}` in a template. Where the six
templates genuinely differ — contact line, skills, experience — the builder takes the
style from the template's own `template.json` rather than branching on its name.
"""

import re
from collections.abc import Iterable, Sequence

from modules.profile import (
    Certification,
    Education,
    Experience,
    Personal,
    ProfileLink,
    SkillGroup,
)

_SPECIALS = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
    # Typography the profile stores as real characters, so no LaTeX leaks into the DB.
    "\u2014": "---",
    "\u2013": "--",
    "\u2019": "'",
    "\u201c": "``",
    "\u201d": "''",
}
_SPECIAL_RE = re.compile("|".join(re.escape(char) for char in _SPECIALS))

_LINK_ICONS = {
    "linkedin": r"\faLinkedin",
    "github": r"\faGithub",
    "gitlab": r"\faGitlab",
    "portfolio": r"\faGlobe",
    "website": r"\faGlobe",
    "twitter": r"\faTwitter",
    "x": r"\faTwitter",
}


def tex(value: str) -> str:
    """Escape one profile value. A single pass, so an escape's own backslash is
    never re-escaped."""
    return _SPECIAL_RE.sub(lambda match: _SPECIALS[match.group()], value)


def _href(url: str, shown: str) -> str:
    target = url if url.startswith(("http://", "https://", "mailto:")) else f"https://{url}"
    # The URL goes in unescaped: \href's first argument is verbatim-ish and escaping
    # it would break the link. Only the visible label is escaped.
    return rf"\href{{{target}}}{{{tex(shown)}}}"


def _icon_for(link: ProfileLink) -> str:
    return _LINK_ICONS.get(link.label.strip().lower(), r"\faLink")


def _date_range(start: str | None, end: str | None, current: bool = False) -> str:
    finish = "Present" if current else (end or "")
    if start and finish:
        return f"{tex(start)} -- {tex(finish)}"
    return tex(start or finish or "")


def _location(value: str | None, style: str) -> str:
    if not value:
        return ""
    # "city" templates print "Bengaluru" where the others print "Bengaluru, India".
    return tex(value.split(",")[0].strip() if style == "city" else value)


def _chunk(items: Sequence[str], buckets: int) -> list[list[str]]:
    """Spread items across a fixed number of buckets, largest first."""
    if buckets < 1:
        return [list(items)]
    size, extra = divmod(len(items), buckets)
    out: list[list[str]] = []
    start = 0
    for index in range(buckets):
        take = size + (1 if index < extra else 0)
        out.append(list(items[start : start + take]))
        start += take
    return out


def contact_block(personal: Personal, email: str, style: str) -> str:
    """The contact line. `contactitem` uses the template's own command; `plain`
    emits bare icons for templates that colour the whole line themselves."""
    entries: list[tuple[str, str]] = []
    if personal.phone:
        entries.append((r"\faPhone", tex(personal.phone)))
    entries.append((r"\faEnvelope", _href(f"mailto:{email}", email)))
    if personal.location:
        entries.append((r"\faMapMarker*", tex(personal.location)))
    entries.extend((_icon_for(link), _href(link.value, link.value)) for link in personal.links)

    if style == "plain":
        joiner = "\\enspace\\enspace\n"
        return joiner.join(rf"{icon}\ {value}" for icon, value in entries)

    joiner = "\\enspace\n  "
    return joiner.join(rf"\contactitem{{{icon}}}{{{value}}}" for icon, value in entries)


def skills_grid(groups: Iterable[SkillGroup], columns: int) -> str:
    """One tabularx row per group, the group's items spread across the columns."""
    rows: list[str] = []
    for group in groups:
        cells = [", ".join(tex(item) for item in bucket) for bucket in _chunk(group.items, columns)]
        rows.append(" & ".join(cells) + r" \\")
    return "\n".join(rows)


def skills_pills(groups: Iterable[SkillGroup]) -> str:
    """Every skill as a \\skilltag in one flow. No manual row breaks: LaTeX wraps the
    paragraph itself, so the layout survives a change in how many skills there are."""
    pills = [rf"\skilltag{{{tex(item)}}}" for group in groups for item in group.items]
    return "\\ ".join(pills)


def _items(bullets: Iterable[str]) -> str:
    return "\n".join(rf"  \item {tex(bullet)}" for bullet in bullets)


def _jobtitle_role(role: Experience, location_style: str) -> str:
    header = (
        rf"\jobtitle{{{tex(role.title)}}}{{{tex(role.company)}}}"
        rf"{{{_date_range(role.start, role.end, role.current)}}}"
        rf"{{{_location(role.location, location_style)}}}"
    )
    parts = [header]
    if role.bullets:
        parts.append("\\begin{itemize}\n" + _items(role.bullets) + "\n\\end{itemize}")
    for project in role.projects:
        parts.append(rf"\projectlabel{{{tex(project.label)}}}")
        parts.append("\\begin{itemize}\n" + _items(project.bullets) + "\n\\end{itemize}")
    return "\n".join(parts)


def _timeline_role(role: Experience, location_style: str) -> str:
    """One tcolorbox per role. Date and location share the third argument, and the
    fourth is a bare \\item list — the command supplies the itemize itself."""
    meta = _date_range(role.start, role.end, role.current)
    where = _location(role.location, location_style)
    if where:
        meta = rf"{meta} \textperiodcentered\ {where}"

    bullets = list(role.bullets)
    for project in role.projects:
        bullets.extend(project.bullets)

    return (
        rf"\timelinerole{{{tex(role.title)}}}{{{tex(role.company)}}}{{{meta}}}{{%"
        + "\n"
        + _items(bullets)
        + "}"
    )


def experience_block(roles: Iterable[Experience], style: str, location_style: str) -> str:
    build = _timeline_role if style == "timelinerole" else _jobtitle_role
    return "\n\n".join(build(role, location_style) for role in roles)


def education_block(entries: Iterable[Education]) -> str:
    rows: list[str] = []
    for entry in entries:
        where = ", ".join(part for part in (entry.institution, entry.location) if part)
        rows.append(
            rf"\educrow{{{tex(entry.degree)}}}{{{tex(where)}}}"
            rf"{{{_date_range(entry.start, entry.end)}}}"
        )
    return "\n".join(rows)


def certifications_block(entries: Iterable[Certification]) -> str:
    return "\n".join(
        rf"\certrow{{{tex(entry.name)}}}{{{tex(entry.issuer)}}}{{{tex(entry.year or '')}}}"
        for entry in entries
    )
