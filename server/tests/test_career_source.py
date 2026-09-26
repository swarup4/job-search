"""The registry scraping reads from, and the result each run writes back."""

from __future__ import annotations

from httpx import AsyncClient

ACCENTURE = {
    "name": "Accenture",
    "careersUrl": "https://accenture.wd103.myworkdayjobs.com/AccentureCareers",
    "platform": "workday",
    "config": {"tenant": "accenture", "wd": "wd103", "site": "AccentureCareers"},
}


async def test_requires_a_token(client: AsyncClient) -> None:
    response = await client.get("/career-source")
    assert response.status_code == 401


async def test_a_name_is_registered_once(signed_in: AsyncClient) -> None:
    first = await signed_in.post("/career-source", json=ACCENTURE)
    assert first.status_code == 201, first.text

    again = await signed_in.post("/career-source", json=ACCENTURE)
    assert again.status_code == 409


async def test_an_unknown_platform_is_refused(signed_in: AsyncClient) -> None:
    response = await signed_in.post("/career-source", json={**ACCENTURE, "platform": "taleo"})
    assert response.status_code == 422


async def test_list_filters_on_enabled(signed_in: AsyncClient) -> None:
    await signed_in.post("/career-source", json=ACCENTURE)
    await signed_in.post(
        "/career-source",
        json={**ACCENTURE, "name": "Zoom", "enabled": False, "notes": "robots.txt"},
    )

    enabled = (await signed_in.get("/career-source", params={"enabled": True})).json()
    assert [row["name"] for row in enabled] == ["Accenture"]

    everything = (await signed_in.get("/career-source")).json()
    assert [row["name"] for row in everything] == ["Accenture", "Zoom"]


async def test_a_run_result_is_recorded(signed_in: AsyncClient) -> None:
    source_id = (await signed_in.post("/career-source", json=ACCENTURE)).json()["id"]

    response = await signed_in.put(
        f"/career-source/result/{source_id}",
        json={"fetched": 40, "matched": 6, "new": 5, "duplicate": 1},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["lastResult"]["new"] == 5
    assert body["lastResult"]["blocked"] is False
    assert body["lastRunAt"] is not None


async def test_patch_changes_only_what_it_sends(signed_in: AsyncClient) -> None:
    source_id = (await signed_in.post("/career-source", json=ACCENTURE)).json()["id"]

    response = await signed_in.patch(f"/career-source/{source_id}", json={"enabled": False})
    body = response.json()
    assert body["enabled"] is False
    assert body["config"] == ACCENTURE["config"]
