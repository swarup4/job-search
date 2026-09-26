"""What discovery looks for, saved per account from the Settings screen."""

from __future__ import annotations

from httpx import AsyncClient

TARGETS = {
    "roles": ["Technical Lead", "Senior Full-Stack Engineer", "GenAI Engineer", "Staff Engineer"],
    "locations": ["Bengaluru", "Remote (India)", "Pune", "Hyderabad"],
    "workMode": "hybrid",
    "minExperience": 6,
}


async def test_requires_a_token(client: AsyncClient) -> None:
    assert (await client.get("/preference")).status_code == 401


async def test_unsaved_reads_back_as_the_defaults(signed_in: AsyncClient) -> None:
    body = (await signed_in.get("/preference")).json()
    assert "LLM" in body["roles"]
    assert body["locations"] == ["India"]
    assert body["workMode"] is None
    assert body["updatedAt"] is None


async def test_a_save_is_read_back(signed_in: AsyncClient) -> None:
    saved = await signed_in.put("/preference", json=TARGETS)
    assert saved.status_code == 200, saved.text
    assert saved.json()["updatedAt"] is not None

    body = (await signed_in.get("/preference")).json()
    assert body["roles"] == TARGETS["roles"]
    assert body["locations"] == TARGETS["locations"]
    assert body["workMode"] == "hybrid"
    assert body["minExperience"] == 6


async def test_a_second_save_replaces_the_first(signed_in: AsyncClient) -> None:
    await signed_in.put("/preference", json=TARGETS)
    await signed_in.put("/preference", json={"roles": ["Agentic"], "locations": ["India"]})

    body = (await signed_in.get("/preference")).json()
    assert body["roles"] == ["Agentic"]
    assert body["workMode"] is None
    assert body["minExperience"] is None


async def test_terms_are_trimmed_and_repeats_dropped(signed_in: AsyncClient) -> None:
    body = (
        await signed_in.put(
            "/preference", json={"roles": [" LLM ", "llm", "", "GenAI"], "locations": ["India"]}
        )
    ).json()
    assert body["roles"] == ["LLM", "GenAI"]


async def test_nothing_to_search_for_is_refused(signed_in: AsyncClient) -> None:
    for roles in ([], ["  "]):
        response = await signed_in.put("/preference", json={"roles": roles, "locations": ["India"]})
        assert response.status_code == 422


async def test_an_unknown_work_mode_is_refused(signed_in: AsyncClient) -> None:
    response = await signed_in.put("/preference", json={**TARGETS, "workMode": "Hybrid preferred"})
    assert response.status_code == 422
