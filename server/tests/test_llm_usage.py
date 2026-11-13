"""The usage log: every model call the AI tier made, stored per account and read
back as totals per step."""

from __future__ import annotations

from typing import Any

from httpx import AsyncClient


def call(step: str, prompt: int, completion: int, **extra: Any) -> dict[str, Any]:
    return {
        "step": step,
        "model": "localhost/qwen3.5:9b",
        "promptVersion": 1,
        "promptTokens": prompt,
        "completionTokens": completion,
        "elapsedMs": 1200,
        **extra,
    }


RUN = {
    "runKind": "scoring",
    "runId": "run-1",
    "calls": [
        call("BriefDraft", 4000, 300),
        call("Comparison", 5000, 200, cachedTokens=3500),
        call("Comparison", 5200, 210, attempt=2),
    ],
}


async def test_requires_a_token(client: AsyncClient) -> None:
    assert (await client.post("/llm-usage", json=RUN)).status_code == 401
    assert (await client.get("/llm-usage/summary")).status_code == 401


async def test_a_run_is_stored_and_totalled_per_step(signed_in: AsyncClient) -> None:
    stored = await signed_in.post("/llm-usage", json=RUN)
    assert stored.status_code == 201, stored.text
    assert stored.json() == {"stored": 3}

    summary = (await signed_in.get("/llm-usage/summary")).json()
    assert summary["calls"] == 3
    assert summary["promptTokens"] == 14200
    assert summary["cachedTokens"] == 3500
    assert summary["completionTokens"] == 710

    # Largest prompt total first.
    assert [step["step"] for step in summary["steps"]] == ["Comparison", "BriefDraft"]
    compare = summary["steps"][0]
    assert (compare["calls"], compare["retries"]) == (2, 1)
    assert compare["averageElapsedMs"] == 1200


async def test_one_run_can_be_read_on_its_own(signed_in: AsyncClient) -> None:
    await signed_in.post("/llm-usage", json=RUN)
    await signed_in.post(
        "/llm-usage",
        json={"runKind": "tailoring", "runId": None, "calls": [call("PlacementPlan", 900, 150)]},
    )

    only = (await signed_in.get("/llm-usage/summary", params={"runId": "run-1"})).json()
    assert only["calls"] == 3
    assert {step["step"] for step in only["steps"]} == {"BriefDraft", "Comparison"}


async def test_prompt_versions_are_totalled_apart(signed_in: AsyncClient) -> None:
    """A before-and-after comparison is made between versions of the same step."""
    await signed_in.post(
        "/llm-usage",
        json={
            "runKind": "scoring",
            "runId": "run-2",
            "calls": [
                call("Comparison", 5000, 200),
                call("Comparison", 3000, 200, promptVersion=2),
            ],
        },
    )

    steps = (await signed_in.get("/llm-usage/summary")).json()["steps"]
    assert [(step["promptVersion"], step["promptTokens"]) for step in steps] == [
        (1, 5000),
        (2, 3000),
    ]


async def test_an_account_sees_only_its_own_usage(client: AsyncClient) -> None:
    first = await client.post(
        "/account/signup",
        json={"name": "One", "email": "one@example.com", "password": "correct-horse"},
    )
    one = {"Authorization": f"Bearer {first.json()['accessToken']}"}
    await client.post("/llm-usage", json=RUN, headers=one)

    second = await client.post(
        "/account/signup",
        json={"name": "Two", "email": "two@example.com", "password": "correct-horse"},
    )
    two = {"Authorization": f"Bearer {second.json()['accessToken']}"}

    assert (await client.get("/llm-usage/summary", headers=two)).json()["calls"] == 0


async def test_an_empty_batch_and_a_negative_count_are_refused(signed_in: AsyncClient) -> None:
    empty = await signed_in.post("/llm-usage", json={"runKind": "scoring", "calls": []})
    assert empty.status_code == 422

    negative = await signed_in.post(
        "/llm-usage", json={"runKind": "scoring", "calls": [call("Comparison", -1, 10)]}
    )
    assert negative.status_code == 422
