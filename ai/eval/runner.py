"""Run the scoring pipeline over a labelled set and report how it did.

    cd ai
    uv run python -m eval.runner --data eval/data --out eval/reports/after.json
    uv run python -m eval.runner --data eval/data --out eval/reports/after.json \\
        --baseline eval/reports/before.json

The first form writes a report. The second also prints it beside an earlier one, which
is how a prompt or model change is judged: accuracy that must not fall, and tokens and
time that should.

It drives the configured model (`ai/.env`) through the same functions a real run uses —
`build_brief`, `build_inventory`, `compare` — and nothing else. No API server, no
account, no database: the labelled set carries the postings and the profiles.

Not measured here: tailoring's decline rate, which needs a user's keyword selection,
and the near-miss flags, which need the vector index.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from agents import inventory, matching, parsing, tailoring
from agents.evidence import profile_corpus
from config import llm
from eval.dataset import LabelledPosting, LabelledSet, load
from eval.metrics import Counts, detail_counts, rates, requirement_counts, verdict_counts

# What a report is compared on, in the order it is printed. True where lower is better.
COMPARED = {
    "requirementPrecision": False,
    "requirementRecall": False,
    "detailAccuracy": False,
    "verdictAccuracy": False,
    "wrongPresentRate": True,
    "wrongMissingRate": True,
    "callsPerPosting": True,
    "promptTokensPerPosting": True,
    "cachedTokensPerPosting": False,
    "completionTokensPerPosting": True,
    "secondsPerPosting": True,
    "retryRate": True,
}


def prompt_versions() -> dict[str, int]:
    return {
        "brief": matching.BRIEF_VERSION,
        "compare": matching.COMPARE_VERSION,
        "inventory": inventory.INVENTORY_VERSION,
        "parse": parsing.PARSE_VERSION,
        "tailor": tailoring.TAILOR_VERSION,
    }


async def evaluate(labelled: LabelledSet) -> dict[str, Any]:
    """Every posting read once, then judged against every profile it is labelled for."""
    counts = Counts()
    failures: list[dict[str, str]] = []
    inventories: dict[str, inventory.Inventory] = {}

    with llm.track_usage() as usage:
        for posting in labelled.postings:
            try:
                counts += await _evaluate_posting(posting, labelled, inventories)
            except llm.GenerationError as error:
                # A posting the model could not answer for is a result, not a crash.
                failures.append({"posting": posting.id, "error": str(error)[:300]})

    postings = len(labelled.postings)
    return {
        "ranAt": datetime.now(UTC).isoformat(timespec="seconds"),
        "models": {
            "brief": llm.BRIEF.provenance,
            "compare": llm.MATCH.provenance,
            "inventory": llm.INVENTORY.provenance,
        },
        "promptVersions": prompt_versions(),
        "postings": postings,
        "profiles": len(labelled.profiles),
        "failures": failures,
        "rates": rates(counts),
        "usage": _usage(usage, postings),
        "steps": _steps(usage),
    }


async def _evaluate_posting(
    posting: LabelledPosting, labelled: LabelledSet, inventories: dict[str, inventory.Inventory]
) -> Counts:
    brief = await matching.build_brief(posting.jdText)
    counts = requirement_counts(
        posting.requirements, [item.label for item in brief.requirements]
    ) + detail_counts(posting.details, brief.details())

    job = {"title": posting.title, "company": posting.company, "location": posting.location}
    for profile_id, expected in posting.verdicts.items():
        candidate = labelled.profile(profile_id)
        if candidate is None:
            raise ValueError(f"posting {posting.id} is labelled for unknown profile {profile_id}")
        if profile_id not in inventories:
            inventories[profile_id] = await _inventory(candidate.profile)
        present, missing, _ = await matching.compare(
            brief, inventories[profile_id], candidate.profile, job
        )
        counts += verdict_counts(
            expected.present,
            expected.missing,
            [item.label for item in present],
            [item.label for item in missing],
        )
    return counts


async def _inventory(profile: dict[str, Any]) -> inventory.Inventory:
    """Built the way `ensure_inventory` builds one, without the store it reads first."""
    corpus = profile_corpus(profile)
    built = await inventory.build_inventory(corpus, inventory.profile_hash(corpus))
    built.candidateBlock = inventory.render_candidate(built.skills, profile)
    return built


def _usage(usage: llm.Usage, postings: int) -> dict[str, float | int | None]:
    """Per posting, so two sets of different sizes compare. The inventory call is
    counted too: it is paid once per profile, and the set says how many there are."""
    calls = usage.records
    per = max(postings, 1)
    retries = sum(1 for call in calls if call.attempt > 1)
    return {
        "calls": len(calls),
        "callsPerPosting": round(len(calls) / per, 2),
        "promptTokensPerPosting": round(usage.prompt_tokens / per),
        "cachedTokensPerPosting": round(usage.cached_tokens / per),
        "completionTokensPerPosting": round(usage.completion_tokens / per),
        "secondsPerPosting": round(sum(call.elapsed_ms for call in calls) / 1000 / per, 1),
        "retryRate": round(retries / len(calls), 4) if calls else None,
    }


def _steps(usage: llm.Usage) -> dict[str, dict[str, int]]:
    """The same totals by step, which is where a change in cost is found."""
    steps: dict[str, dict[str, int]] = defaultdict(
        lambda: dict.fromkeys(
            ("calls", "retries", "promptTokens", "cachedTokens", "completionTokens", "elapsedMs"),
            0,
        )
    )
    for call in usage.records:
        step = steps[call.step]
        step["calls"] += 1
        step["retries"] += call.attempt > 1
        step["promptTokens"] += call.prompt_tokens
        step["cachedTokens"] += call.cached_tokens
        step["completionTokens"] += call.completion_tokens
        step["elapsedMs"] += call.elapsed_ms
    return dict(steps)


# --- before and after ---------------------------------------------------------


def compare_reports(before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
    """One row per measure: both values, the change, and whether it got worse."""
    rows = []
    for name, lower_is_better in COMPARED.items():
        old = {**before.get("rates", {}), **before.get("usage", {})}.get(name)
        new = {**after.get("rates", {}), **after.get("usage", {})}.get(name)
        change = None if old is None or new is None else round(new - old, 4)
        worse = bool(change) and (change > 0) == lower_is_better
        rows.append(
            {"measure": name, "before": old, "after": new, "change": change, "worse": worse}
        )
    return rows


def render(report: dict[str, Any], baseline: dict[str, Any] | None = None) -> str:
    sizes = f"{report['postings']} postings, {report['profiles']} profiles"
    versions = ", ".join(f"{step} v{number}" for step, number in report["promptVersions"].items())
    lines = [
        f"{sizes} — compare on {report['models']['compare']}",
        f"prompt versions: {versions}",
    ]
    if report["failures"]:
        lines.append(f"{len(report['failures'])} postings failed: see `failures` in the report")

    if baseline is None:
        values = {**report["rates"], **report["usage"]}
        lines += [f"  {name:<28} {_show(values.get(name))}" for name in COMPARED]
        return "\n".join(lines)

    if baseline.get("promptVersions") == report["promptVersions"] and baseline.get(
        "models"
    ) == report.get("models"):
        lines.append("note: same prompt versions and models as the baseline")
    lines.append(f"  {'measure':<28} {'before':>10} {'after':>10} {'change':>10}")
    for row in compare_reports(baseline, report):
        flag = "  WORSE" if row["worse"] else ""
        lines.append(
            f"  {row['measure']:<28} {_show(row['before']):>10} {_show(row['after']):>10} "
            f"{_show(row['change'], signed=True):>10}{flag}"
        )
    return "\n".join(lines)


def _show(value: float | None, signed: bool = False) -> str:
    if value is None:
        return "n/a"
    return f"{value:+g}" if signed else f"{value:g}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    parser.add_argument("--data", type=Path, required=True, help="a labelled set: file or folder")
    parser.add_argument("--out", type=Path, required=True, help="where to write the report")
    parser.add_argument("--baseline", type=Path, help="an earlier report to compare against")
    args = parser.parse_args(argv)

    report = asyncio.run(evaluate(load(args.data)))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    baseline = json.loads(args.baseline.read_text(encoding="utf-8")) if args.baseline else None
    print(render(report, baseline))
    print(f"report written to {args.out}")
    # A run that got worse on a measure exits non-zero, so CI can gate on it.
    worse = baseline is not None and any(row["worse"] for row in compare_reports(baseline, report))
    return 1 if worse else 0


if __name__ == "__main__":
    sys.exit(main())
