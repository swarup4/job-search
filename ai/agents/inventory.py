"""The profile read once into a skill inventory: every skill it shows, each tied to
the profile line that shows it.

Scoring compares a job against this instead of against the whole profile, so the
profile is read by the model once per edit rather than once per job. An entry whose
quote is not in the profile is dropped before it is stored — every skill a later
comparison cites has already been checked against what the user actually wrote.
"""

from __future__ import annotations

import asyncio
import hashlib
import sys
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

from agents.evidence import flatten, profile_corpus, slug, verified_span
from config.llm import INVENTORY, UNTRUSTED_RULE, as_document, generate
from mcp_servers import jobpilot_api

# Bumped when the prompt changes, so an inventory read under the old one is rebuilt.
INVENTORY_VERSION = 1

MAX_SKILLS = 100
# A skill list is long output: about fifty tokens an entry.
MAX_OUTPUT_TOKENS = 6_144

Kind = Literal["tech", "qualification", "practice"]

KIND_RULE = (
    '`kind` is "tech" for something you could install, import or sign up for — a '
    "language, framework, library, database, cloud service, platform or protocol "
    '("Python", "LangGraph", "PostgreSQL", "AWS"). "qualification" for years of '
    'experience, degrees and certifications. "practice" for methodologies and '
    'disciplines ("Agile", "prompt engineering", "MLOps").'
)

INVENTORY_SYSTEM = f"""You read a candidate's profile and list every skill it shows.

{UNTRUSTED_RULE}

Rules:
- A skill is a technology, tool, platform, methodology, certification or qualification the profile shows the candidate has — in any role, however old.
- `label` is the profile's own name for it, at most four words.
- `aliases` are other names a job description might use for exactly the same skill, e.g. "k8s" for "Kubernetes". True synonyms only, never related skills. At most 3.
- {KIND_RULE}
- `source` names where it appears: the role and company, or "Skills", "Education", "Certifications".
- `evidence` is one line copied VERBATIM from the profile that shows the skill. Never join lines, never add section names or prefixes.
- List each skill once. At most {MAX_SKILLS}, most significant first."""


# Capped so the grammar Ollama builds from the schema stops a runaway string — see the
# note on SHORT in matching.py.
class DraftSkill(BaseModel):
    label: str = Field(max_length=80)
    aliases: list[Annotated[str, Field(max_length=60)]] = Field(max_length=3)
    kind: Kind
    source: str = Field(max_length=120)
    evidence: str = Field(max_length=400)


class DraftInventory(BaseModel):
    skills: list[DraftSkill] = Field(max_length=MAX_SKILLS)


class Skill(BaseModel):
    id: str
    label: str
    aliases: list[str] = Field(default_factory=list)
    kind: Kind
    source: str = ""
    evidence: str


class Inventory(BaseModel):
    profileHash: str
    modelName: str
    skills: list[Skill]


# Two jobs scored side by side would otherwise both find no inventory and both pay to
# build one.
_building = asyncio.Lock()


def profile_hash(corpus: str) -> str:
    """Changes when the profile text, the prompt version or the model changes — any of
    which makes the stored reading out of date."""
    seed = f"{INVENTORY_VERSION}|{INVENTORY.provenance}|{corpus}"
    return hashlib.sha256(seed.encode()).hexdigest()


async def ensure_inventory(profile: dict[str, Any]) -> Inventory:
    """The stored inventory if it was read from this profile, else a fresh one."""
    corpus = profile_corpus(profile)
    digest = profile_hash(corpus)
    async with _building:
        stored = await jobpilot_api.get_skill_inventory()
        if stored is not None and stored.get("profileHash") == digest:
            return Inventory.model_validate(stored)
        inventory = await build_inventory(corpus, digest)
        await jobpilot_api.replace_skill_inventory(inventory.model_dump())
        return inventory


async def build_inventory(corpus: str, digest: str) -> Inventory:
    draft = await generate(
        DraftInventory,
        as_document("profile", corpus),
        system=INVENTORY_SYSTEM,
        max_tokens=MAX_OUTPUT_TOKENS,
        endpoint=INVENTORY,
    )
    flat_profile = flatten(corpus)
    skills: list[Skill] = []
    seen: set[str] = set()
    for entry in draft.skills:
        label = entry.label.strip()
        key = slug(label)
        if not key or len(label) > 80 or key in seen:
            continue
        evidence = verified_span(entry.evidence, flat_profile)
        if evidence is None:
            continue
        seen.add(key)
        aliases = [alias.strip() for alias in entry.aliases if 0 < len(alias.strip()) <= 80]
        skills.append(
            Skill(
                id=f"s{len(skills) + 1}",
                label=label,
                aliases=aliases[:3],
                kind=entry.kind,
                source=entry.source.strip()[:200],
                evidence=evidence[:1_000],
            )
        )
        if len(skills) == MAX_SKILLS:
            break
    return Inventory(profileHash=digest, modelName=INVENTORY.provenance, skills=skills)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python -m agents.inventory <jwt>")
        sys.exit(1)

    async def main() -> None:
        jobpilot_api.set_token(sys.argv[1])
        inventory = await ensure_inventory(await jobpilot_api.get_profile())
        print(f"{len(inventory.skills)} skills via {inventory.modelName}")
        for skill in inventory.skills:
            print(f"  {skill.id:<4} {skill.label:<28} {skill.kind:<13} {skill.evidence[:60]}")

    asyncio.run(main())
