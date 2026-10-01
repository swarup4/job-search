"""The skill inventory: read once per profile, and never holding a skill the profile
cannot show."""

from __future__ import annotations

from typing import Any

import pytest

from agents import inventory
from agents.evidence import profile_corpus
from agents.inventory import DraftInventory, DraftSkill

PROFILE = {
    "name": "A Candidate",
    "role": "GenAI Engineer",
    "profile": {"headline": "GenAI engineer"},
    "work": [
        {
            "title": "GenAI Engineer",
            "company": "Acme",
            "start": "2023",
            "current": True,
            "bullets": ["Built a LangGraph supervisor over five agents"],
            "projects": [],
        }
    ],
    "skill": [{"name": "Cloud", "items": ["Kubernetes", "Docker"]}],
    "education": [],
    "certification": [],
}


def skill(label: str, evidence: str, aliases: list[str] | None = None) -> DraftSkill:
    return DraftSkill(
        label=label, aliases=aliases or [], kind="tech", source="Acme", evidence=evidence
    )


class Server:
    def __init__(self, stored: dict[str, Any] | None = None) -> None:
        self.stored = stored
        self.replaced: list[dict[str, Any]] = []

    async def get_skill_inventory(self) -> dict[str, Any] | None:
        return self.stored

    async def replace_skill_inventory(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.replaced.append(payload)
        self.stored = payload
        return payload


@pytest.fixture
def server(monkeypatch: pytest.MonkeyPatch) -> Server:
    fake = Server()
    monkeypatch.setattr(inventory.jobpilot_api, "get_skill_inventory", fake.get_skill_inventory)
    monkeypatch.setattr(
        inventory.jobpilot_api, "replace_skill_inventory", fake.replace_skill_inventory
    )
    return fake


def model(*replies: DraftInventory, prompts: list[str] | None = None):
    queue = list(replies)

    async def fake(shape, prompt, *, system, max_tokens=2048, endpoint=None):
        if prompts is not None:
            prompts.append(prompt)
        return queue.pop(0)

    return fake


async def test_a_skill_whose_quote_is_not_in_the_profile_is_dropped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        inventory,
        "generate",
        model(
            DraftInventory(
                skills=[
                    skill("LangGraph", "Built a LangGraph supervisor over five agents"),
                    skill("Rust", "Rewrote the scheduler in Rust for speed"),
                ]
            )
        ),
    )

    built = await inventory.build_inventory(profile_corpus(PROFILE), "h")

    assert [entry.label for entry in built.skills] == ["LangGraph"]


async def test_ids_run_in_order_and_a_repeated_skill_is_listed_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        inventory,
        "generate",
        model(
            DraftInventory(
                skills=[
                    skill("Kubernetes", "Cloud: Kubernetes, Docker", aliases=["k8s"]),
                    skill("kubernetes", "Cloud: Kubernetes, Docker"),
                    skill("Docker", "Cloud: Kubernetes, Docker"),
                ]
            )
        ),
    )

    built = await inventory.build_inventory(profile_corpus(PROFILE), "h")

    assert [(entry.id, entry.label) for entry in built.skills] == [
        ("s1", "Kubernetes"),
        ("s2", "Docker"),
    ]
    assert built.skills[0].aliases == ["k8s"]


async def test_the_profile_reaches_the_model_fenced(monkeypatch: pytest.MonkeyPatch) -> None:
    prompts: list[str] = []
    monkeypatch.setattr(inventory, "generate", model(DraftInventory(skills=[]), prompts=prompts))

    await inventory.build_inventory(profile_corpus(PROFILE), "h")

    assert prompts[0].startswith('<document name="profile">')


async def test_an_inventory_read_from_this_profile_is_reused(
    monkeypatch: pytest.MonkeyPatch, server: Server
) -> None:
    async def refuse(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("the model was called for an up-to-date inventory")

    monkeypatch.setattr(inventory, "generate", refuse)
    digest = inventory.profile_hash(profile_corpus(PROFILE))
    server.stored = {"profileHash": digest, "modelName": "m", "skills": [], "builtAt": "x"}

    found = await inventory.ensure_inventory(PROFILE)

    assert found.profileHash == digest
    assert server.replaced == []


async def test_an_edited_profile_is_read_again_and_stored(
    monkeypatch: pytest.MonkeyPatch, server: Server
) -> None:
    monkeypatch.setattr(
        inventory,
        "generate",
        model(DraftInventory(skills=[skill("Docker", "Cloud: Kubernetes, Docker")])),
    )
    server.stored = {"profileHash": "from-before-the-edit", "modelName": "m", "skills": []}

    found = await inventory.ensure_inventory(PROFILE)

    [written] = server.replaced
    assert written["profileHash"] == inventory.profile_hash(profile_corpus(PROFILE))
    assert [entry["label"] for entry in written["skills"]] == ["Docker"]
    assert [entry.label for entry in found.skills] == ["Docker"]


async def test_none_stored_yet_is_built(monkeypatch: pytest.MonkeyPatch, server: Server) -> None:
    monkeypatch.setattr(inventory, "generate", model(DraftInventory(skills=[])))

    await inventory.ensure_inventory(PROFILE)

    assert len(server.replaced) == 1


def test_the_hash_follows_the_profile_text() -> None:
    edited = {**PROFILE, "skill": [{"name": "Cloud", "items": ["Kubernetes"]}]}

    assert inventory.profile_hash(profile_corpus(PROFILE)) == inventory.profile_hash(
        profile_corpus(PROFILE)
    )
    assert inventory.profile_hash(profile_corpus(PROFILE)) != inventory.profile_hash(
        profile_corpus(edited)
    )
