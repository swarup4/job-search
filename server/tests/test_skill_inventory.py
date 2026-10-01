"""The profile read into skills, stored per account and replaced whole on rebuild."""

from __future__ import annotations

from typing import Any

from httpx import AsyncClient

INVENTORY: dict[str, Any] = {
    "profileHash": "a" * 64,
    "modelName": "localhost/qwen3.5-9b-16k",
    "skills": [
        {"id": "s1", "label": "LangGraph", "aliases": ["multi-agent orchestration"],
         "kind": "tech", "source": "GenAI Engineer — Acme",
         "evidence": "Built a LangGraph supervisor over five agents"},
        {"id": "s2", "label": "Kubernetes", "aliases": ["k8s"], "kind": "tech",
         "evidence": "Deployed services to EKS"},
    ],
}  # fmt: skip


async def test_requires_a_token(client: AsyncClient) -> None:
    assert (await client.get("/skill-inventory/getInventory")).status_code == 401
    response = await client.put("/skill-inventory/replaceInventory", json=INVENTORY)
    assert response.status_code == 401


async def test_none_built_yet_is_404(signed_in: AsyncClient) -> None:
    assert (await signed_in.get("/skill-inventory/getInventory")).status_code == 404


async def test_a_stored_inventory_is_read_back(signed_in: AsyncClient) -> None:
    stored = await signed_in.put("/skill-inventory/replaceInventory", json=INVENTORY)
    assert stored.status_code == 200, stored.text

    body = (await signed_in.get("/skill-inventory/getInventory")).json()
    assert body["profileHash"] == "a" * 64
    assert [skill["id"] for skill in body["skills"]] == ["s1", "s2"]
    assert body["skills"][0]["aliases"] == ["multi-agent orchestration"]
    assert body["skills"][1]["source"] == ""
    assert body["builtAt"] is not None


async def test_a_rebuild_replaces_every_entry(signed_in: AsyncClient) -> None:
    await signed_in.put("/skill-inventory/replaceInventory", json=INVENTORY)
    first = (await signed_in.get("/skill-inventory/getInventory")).json()

    rebuilt = {**INVENTORY, "profileHash": "b" * 64, "skills": INVENTORY["skills"][1:]}
    await signed_in.put("/skill-inventory/replaceInventory", json=rebuilt)

    body = (await signed_in.get("/skill-inventory/getInventory")).json()
    assert body["profileHash"] == "b" * 64
    assert [skill["id"] for skill in body["skills"]] == ["s2"]
    assert body["builtAt"] > first["builtAt"]


async def test_each_account_has_its_own(signed_in: AsyncClient) -> None:
    await signed_in.put("/skill-inventory/replaceInventory", json=INVENTORY)

    other = await signed_in.post(
        "/account/signup",
        json={"name": "Other", "email": "other@example.com", "password": "correct-horse"},
    )
    signed_in.headers["Authorization"] = f"Bearer {other.json()['accessToken']}"
    assert (await signed_in.get("/skill-inventory/getInventory")).status_code == 404


async def test_repeated_ids_are_refused(signed_in: AsyncClient) -> None:
    twice = {**INVENTORY, "skills": [INVENTORY["skills"][0]] * 2}

    response = await signed_in.put("/skill-inventory/replaceInventory", json=twice)
    assert response.status_code == 422


async def test_an_entry_without_evidence_is_refused(signed_in: AsyncClient) -> None:
    bare = {**INVENTORY, "skills": [{**INVENTORY["skills"][0], "evidence": ""}]}

    response = await signed_in.put("/skill-inventory/replaceInventory", json=bare)
    assert response.status_code == 422
