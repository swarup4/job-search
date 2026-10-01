"""A posting read once into a brief, stored beside the description it came from."""

from __future__ import annotations

from typing import Any

from httpx import AsyncClient

TEXT = "Senior Backend Engineer. 5+ years of Python. Kubernetes required. Hybrid in Bengaluru."

BRIEF: dict[str, Any] = {
    "requirements": [
        {"key": "python", "label": "Python", "kind": "tech", "mentions": 1,
         "evidence": "5+ years of Python"},
        {"key": "kubernetes", "label": "Kubernetes", "kind": "tech",
         "evidence": "Kubernetes required"},
    ],
    "seniority": "Senior",
    "minYears": 5,
    "locationRule": "Hybrid in Bengaluru",
    "workMode": "hybrid",
    "modelName": "localhost/qwen3.5-9b-16k",
    "briefVersion": 1,
}  # fmt: skip


async def capture(client: AsyncClient) -> str:
    response = await client.post(
        "/job-description",
        json={
            "url": "https://acme.example/jobs/1",
            "pageTitle": "Senior Backend Engineer",
            "markdown": TEXT,
            "region": "feed",
            "textLength": len(TEXT),
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def test_requires_a_token(client: AsyncClient) -> None:
    response = await client.put("/job-description/storeBrief/0123456789abcdef01234567", json=BRIEF)
    assert response.status_code == 401


async def test_a_description_starts_without_a_brief(signed_in: AsyncClient) -> None:
    description_id = await capture(signed_in)

    body = (await signed_in.get(f"/job-description/{description_id}")).json()
    assert body["brief"] is None


async def test_a_stored_brief_comes_back_with_the_description(signed_in: AsyncClient) -> None:
    description_id = await capture(signed_in)

    stored = await signed_in.put(f"/job-description/storeBrief/{description_id}", json=BRIEF)
    assert stored.status_code == 200, stored.text

    brief = (await signed_in.get(f"/job-description/{description_id}")).json()["brief"]
    assert [item["key"] for item in brief["requirements"]] == ["python", "kubernetes"]
    assert brief["requirements"][1]["mentions"] == 1
    assert (brief["minYears"], brief["workMode"], brief["briefVersion"]) == (5, "hybrid", 1)
    assert brief["builtAt"] is not None


async def test_a_second_brief_replaces_the_first(signed_in: AsyncClient) -> None:
    description_id = await capture(signed_in)
    await signed_in.put(f"/job-description/storeBrief/{description_id}", json=BRIEF)

    newer = {**BRIEF, "requirements": BRIEF["requirements"][:1], "briefVersion": 2}
    await signed_in.put(f"/job-description/storeBrief/{description_id}", json=newer)

    brief = (await signed_in.get(f"/job-description/{description_id}")).json()["brief"]
    assert [item["key"] for item in brief["requirements"]] == ["python"]
    assert brief["briefVersion"] == 2


async def test_a_listing_does_not_carry_the_brief(signed_in: AsyncClient) -> None:
    description_id = await capture(signed_in)
    await signed_in.put(f"/job-description/storeBrief/{description_id}", json=BRIEF)

    rows = (await signed_in.get("/job-description")).json()
    assert "brief" not in rows[0]


async def test_repeated_requirement_keys_are_refused(signed_in: AsyncClient) -> None:
    description_id = await capture(signed_in)
    twice = {**BRIEF, "requirements": [BRIEF["requirements"][0]] * 2}

    response = await signed_in.put(f"/job-description/storeBrief/{description_id}", json=twice)
    assert response.status_code == 422


async def test_an_unknown_kind_is_refused(signed_in: AsyncClient) -> None:
    description_id = await capture(signed_in)
    bad = {**BRIEF, "requirements": [{**BRIEF["requirements"][0], "kind": "soft-skill"}]}

    response = await signed_in.put(f"/job-description/storeBrief/{description_id}", json=bad)
    assert response.status_code == 422


async def test_a_brief_for_a_missing_description_is_404(signed_in: AsyncClient) -> None:
    response = await signed_in.put(
        "/job-description/storeBrief/0123456789abcdef01234567", json=BRIEF
    )
    assert response.status_code == 404
