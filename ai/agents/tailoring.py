"""The resume tailoring capability: place the keywords the user ticked, and nothing else.

The `.tex` never reaches the model. It is handed the candidate's current role and
their skill groups as data, and answers with *placement* — which skill group a
keyword joins, or which existing bullet it belongs in and how that bullet reads
afterwards. So it cannot touch the preamble, and it cannot alter education,
certifications or the closed-out roles, because it never sees them.

Two checks stand between that answer and the file:

1. a keyword the user did not tick is refused outright;
2. a rewritten bullet may introduce no word that is not either the keyword itself or
   an ordinary connective — which means no new employer, metric, date, tool or claim.

A keyword that fails either check is declined and reported, never smoothed over. The
server then re-checks the first of these when the resume is stored, so the guarantee
does not depend on this process behaving. (FR-4.2, NFR-8)
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel

from config.llm import generate
from config.settings import settings
from mcp_servers import jobpilot_api

# Words a rewrite may introduce on its own. Deliberately dull and deliberately short:
# anything carrying meaning has to come from the original bullet or the keyword.
CONNECTIVES = frozenset(
    [
        "a",
        "an",
        "and",
        "as",
        "at",
        "by",
        "for",
        "from",
        "in",
        "including",
        "into",
        "of",
        "on",
        "or",
        "plus",
        "the",
        "to",
        "using",
        "via",
        "with",
        "within",
    ]
)


class SelectionGateNotPassed(RuntimeError):
    """Tailoring asked for before the user answered the interrupt."""


class NoCurrentRole(RuntimeError):
    """Nothing to tailor: the profile holds no work experience."""


class Placement(BaseModel):
    keyword: str
    kind: Literal["skill", "bullet"]
    group: str
    bullet: str
    rewritten: str


class PlacementPlan(BaseModel):
    placements: list[Placement]


class Declined(BaseModel):
    """A keyword left out, and why. The reason is the point — FR-4.2 says the honest
    answer to "this does not fit" is to say so."""

    label: str
    reason: str


TAILOR_SYSTEM = """You place keywords a candidate has already approved into their existing resume. You never write new experience.

You are given the candidate's current role with its bullet points, their skill groups, and the approved keywords.

For each keyword choose at most one placement:
- "skill" — the keyword is a technology belonging in one of the EXISTING skill groups. Name that group exactly.
- "bullet" — the keyword describes work an existing bullet already covers. Copy that bullet VERBATIM into `bullet`, and put the smallest possible edit of it into `rewritten`.

Rules for a rewrite:
- Keep every fact of the original: the same employer, the same numbers, the same outcome.
- Introduce no new achievement, metric, date, tool, client or claim. The only new words may be the keyword itself and ordinary connecting words.
- Leave unused fields as an empty string.

If a keyword has no honest home in this resume, leave it out of your answer entirely. Leaving it out is correct and expected — inventing a place for it is not."""


async def tailor(job_id: str) -> dict[str, Any]:
    """Tailor the stored base resume for one job and record it through `server`."""
    match = await jobpilot_api.get_match(job_id)
    selected = _selected_labels(match)

    profile = await jobpilot_api.get_profile()
    base = await jobpilot_api.get_base_resume()

    role = _current_role(profile)
    groups = profile.get("skill", [])
    plan = await plan_placements(selected, role, groups)

    accepted, declined = review(plan, selected, role, groups)
    tex, changes = apply(base["tex"], accepted, groups)

    path = _write(job_id, tex)
    return await jobpilot_api.store_resume(
        {
            "jobId": job_id,
            "filePath": str(path),
            "incorporated": [item.keyword for item in accepted],
            "declined": [item.label for item in declined],
            "changes": changes,
        }
    )


def _selected_labels(match: dict[str, Any]) -> list[str]:
    """The user's answer at the keyword interrupt, as labels.

    Raises rather than tailoring an unreviewed match. The server refuses this too;
    the check is here as well so a run fails before it writes a file. (FR-7.3)
    """
    review_state = (match.get("review") or {}).get("state")
    if review_state != "selected":
        raise SelectionGateNotPassed(
            f"the keyword gate for this job is '{review_state}', not 'selected'"
        )

    keys = set((match.get("review") or {}).get("selectedKeys", []))
    labels = [item["label"] for item in match.get("missing", []) if item["key"] in keys]
    if not labels:
        raise SelectionGateNotPassed(
            "the user selected no keywords, so there is nothing to incorporate"
        )
    return labels


# --- the model's part: placement, never prose --------------------------------


async def plan_placements(
    labels: list[str], role: dict[str, Any], groups: list[dict[str, Any]]
) -> PlacementPlan:
    listing = "\n".join(f"- {label}" for label in labels)
    bullets = "\n".join(f"- {bullet}" for bullet in role.get("bullets", []))
    skills = "\n".join(
        f"- {group.get('name', '')}: {', '.join(group.get('items', []))}" for group in groups
    )

    return await generate(
        PlacementPlan,
        f"Approved keywords:\n{listing}\n\n"
        f"Current role: {role.get('title', '')} at {role.get('company', '')}\n"
        f"Bullet points:\n{bullets}\n\n"
        f"Skill groups:\n{skills}",
        system=TAILOR_SYSTEM,
    )


# --- the checks --------------------------------------------------------------


def review(
    plan: PlacementPlan,
    selected: list[str],
    role: dict[str, Any],
    groups: list[dict[str, Any]],
) -> tuple[list[Placement], list[Declined]]:
    """Keep the placements that survive scrutiny; say why the others did not."""
    allowed = {_flat(label): label for label in selected}
    group_names = {_flat(group.get("name", "")) for group in groups}
    bullets = {_flat(bullet): bullet for bullet in role.get("bullets", [])}

    accepted: list[Placement] = []
    placed: set[str] = set()
    reasons: dict[str, str] = {}

    for placement in plan.placements:
        label = allowed.get(_flat(placement.keyword))
        if label is None:
            # Not a refusal to record against a keyword — the model named something
            # the user never ticked, and it simply does not go in.
            continue
        if label in placed:
            continue

        problem = _fault(placement, label, group_names, bullets)
        if problem:
            reasons[label] = problem
            continue

        placed.add(label)
        accepted.append(
            Placement(
                keyword=label,
                kind=placement.kind,
                group=placement.group.strip(),
                bullet=bullets.get(_flat(placement.bullet), ""),
                rewritten=placement.rewritten.strip(),
            )
        )

    declined = [
        Declined(label=label, reason=reasons.get(label, "the model found no honest place for it"))
        for label in selected
        if label not in placed
    ]
    return accepted, declined


def _fault(
    placement: Placement,
    label: str,
    group_names: set[str],
    bullets: dict[str, str],
) -> str | None:
    if placement.kind == "skill":
        if _flat(placement.group) not in group_names:
            return f"'{placement.group}' is not one of the resume's skill groups"
        return None

    original = bullets.get(_flat(placement.bullet))
    if original is None:
        return "the bullet it rewrites is not one of the current role's bullets"

    rewritten = placement.rewritten.strip()
    if not rewritten:
        return "no rewritten bullet was given"
    if _flat(label) not in _flat(rewritten):
        return "the rewritten bullet does not contain the keyword"

    invented = invented_words(original, rewritten, label)
    if invented:
        return "the rewrite adds wording the resume does not support: " + ", ".join(invented)
    return None


def invented_words(original: str, rewritten: str, keyword: str) -> list[str]:
    """Words in the rewrite that came from neither the original bullet nor the keyword.

    This is what stops a rewrite from arriving with a metric, a client or a tool
    nobody claimed. Numbers are words here too, so `40%` where the original said
    `30%` is caught by the same check.
    """
    allowed = _words(original) | _words(keyword) | CONNECTIVES
    seen: list[str] = []
    for word in _word_list(rewritten):
        if word not in allowed and word not in seen:
            seen.append(word)
    return seen


# --- the file ----------------------------------------------------------------


def apply(
    tex: str, accepted: list[Placement], groups: list[dict[str, Any]]
) -> tuple[str, list[dict[str, Any]]]:
    """Fold the accepted placements into the stored `.tex`, line by line.

    A placement whose line cannot be found is dropped rather than guessed at — the
    base resume has moved on since it was rendered, and inventing a place to put the
    text is exactly what this pipeline must not do.
    """
    lines = tex.splitlines()
    # Keyed by line, because two keywords often land on the same one — the skills
    # row. The diff screen should show that line changing once, from what it was to
    # what it ends up as, not once per keyword.
    edits: dict[int, dict[str, Any]] = {}
    by_group = {_flat(group.get("name", "")): group.get("items", []) for group in groups}
    # Each skill is inserted after the previous one, so a group gains them in the
    # order the user ticked them rather than in reverse.
    anchors: dict[str, str] = {}

    for placement in accepted:
        if placement.kind == "bullet":
            index = _line_with(lines, _tex(placement.bullet))
            if index is None:
                continue
            previous = lines[index]
            lines[index] = previous.replace(_tex(placement.bullet), _tex(placement.rewritten))
        else:
            group = _flat(placement.group)
            anchor = anchors.get(group) or _last_item(by_group.get(group, []))
            index = _line_with(lines, _tex(anchor)) if anchor else None
            if index is None:
                continue
            previous = lines[index]
            lines[index] = _add_skill(previous, _tex(anchor), _tex(placement.keyword))
            anchors[group] = placement.keyword

        edit = edits.setdefault(index, {"lineNo": index + 1, "previous": previous})
        edit["text"] = lines[index]

    changes = [edits[index] for index in sorted(edits)]
    return "\n".join(lines) + ("\n" if tex.endswith("\n") else ""), changes


def _add_skill(line: str, anchor: str, addition: str) -> str:
    """Put the new skill directly after the group's last item, in whatever form the
    line already uses — a `\\skilltag` for the pill templates, a comma for the rest."""
    if r"\skilltag{" in line:
        return line.replace(
            rf"\skilltag{{{anchor}}}", rf"\skilltag{{{anchor}}}\ \skilltag{{{addition}}}", 1
        )
    return line.replace(anchor, f"{anchor}, {addition}", 1)


def _line_with(lines: list[str], needle: str) -> int | None:
    if not needle:
        return None
    for index, line in enumerate(lines):
        if needle in line:
            return index
    return None


def _last_item(items: list[str]) -> str:
    return items[-1] if items else ""


def _write(job_id: str, tex: str) -> Path:
    """One `.tex` per run. No PDF — FR-4.4 defers compilation to a later version."""
    settings.tailored_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = settings.tailored_dir / f"{job_id}-{stamp}.tex"
    path.write_text(tex, encoding="utf-8")
    return path


# --- profile and text helpers ------------------------------------------------


def _current_role(profile: dict[str, Any]) -> dict[str, Any]:
    """Only the current role is in play. The closed-out roles are rendered verbatim
    every time, which is why the model is never shown them."""
    work = profile.get("work", [])
    if not work:
        raise NoCurrentRole("the profile has no work experience to tailor")
    for entry in work:
        if entry.get("current"):
            return entry
    return max(work, key=lambda entry: entry.get("start") or "")


# Mirrors server/modules/template/latex.py. The tiers do not import each other, and
# P7-02 takes this over when the `latex` MCP server lands.
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
    "—": "---",
    "–": "--",
    "’": "'",
    "“": "``",
    "”": "''",
}
_SPECIAL_RE = re.compile("|".join(re.escape(char) for char in _SPECIALS))
_WORD_RE = re.compile(r"[a-z0-9]+")


def _tex(value: str) -> str:
    return _SPECIAL_RE.sub(lambda match: _SPECIALS[match.group()], value)


def _flat(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().lower()


def _word_list(value: str) -> list[str]:
    return _WORD_RE.findall(value.lower())


def _words(value: str) -> set[str]:
    return set(_word_list(value))


if __name__ == "__main__":
    import asyncio
    import sys

    async def main() -> None:
        job_id = sys.argv[1] if len(sys.argv) > 1 else ""
        if not job_id:
            print("usage: python agents/tailoring.py <job_id>")
            return
        resume = await tailor(job_id)
        print(f"v{resume['version']} -> {resume['filePath']}")
        print("incorporated:", resume["incorporated"])
        print("declined:    ", resume["declined"])

    asyncio.run(main())
