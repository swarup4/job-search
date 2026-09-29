"""`GET /status` — every number the dashboard shows outside a page's own list, in one
read: the badges, the Pipeline totals, job counts, the last discovery, the profile."""

from __future__ import annotations

from httpx import AsyncClient

from tests.test_board import make_job, score, sign_up, stage


async def status(client: AsyncClient) -> dict:
    response = await client.get("/status")
    assert response.status_code == 200, response.text
    return response.json()


async def test_status_needs_a_token(client: AsyncClient) -> None:
    assert (await client.get("/status")).status_code == 401


async def test_a_new_account_reads_all_zeros(signed_in: AsyncClient) -> None:
    body = await status(signed_in)

    assert body["badges"] == {
        "keywordSelections": 0, "nextJobId": None, "shortlisted": 0, "staged": 0, "pending": 0,
    }  # fmt: skip
    assert body["jobs"] == {"total": 0, "unscored": 0, "analyzed": 0}
    assert body["discovery"]["lastRunAt"] is None and body["discovery"]["companies"] == 0
    assert body["profile"]["hasDefaultResume"] is False
    assert body["serverTime"]


async def test_badges_name_the_longest_waiting_job(signed_in: AsyncClient) -> None:
    older = await make_job(signed_in, "LLM Engineer", "R1")
    newer = await make_job(signed_in, "GenAI Engineer", "R2")
    await score(signed_in, older, 70)
    await score(signed_in, newer, 90)

    badges = (await status(signed_in))["badges"]

    assert badges["keywordSelections"] == 2
    assert badges["nextJobId"] == older


async def test_badges_pipeline_and_jobs_agree(signed_in: AsyncClient) -> None:
    fresh = await make_job(signed_in, "Fresh Role", "R1")
    shortlisted = await make_job(signed_in, "LLM Engineer", "R2")
    staged = await make_job(signed_in, "GenAI Engineer", "R3")
    await score(signed_in, shortlisted, 72)
    await signed_in.post(f"/application/shortlist/{shortlisted}")
    await stage(signed_in, staged)

    body = await status(signed_in)

    assert (body["badges"]["shortlisted"], body["badges"]["staged"]) == (1, 1)
    # One keyword choice waiting plus one staged application.
    assert body["badges"]["pending"] == 2
    assert body["pipeline"] == {
        "new": 1,
        "shortlisted": 1,
        "staged": 1,
        "applied": 0,
        "interview": 0,
    }
    assert body["jobs"] == {"total": 3, "unscored": 2, "analyzed": 1}
    assert fresh


async def test_the_last_discovery_sums_what_each_company_stored(signed_in: AsyncClient) -> None:
    ids = []
    for name in ("Acme", "Globex", "Initech"):
        created = await signed_in.post(
            "/career-source",
            json={"name": name, "platform": "workday", "config": {"tenant": name.lower()}},
        )
        assert created.status_code == 201, created.text
        ids.append(created.json()["id"])
    await signed_in.put(f"/career-source/result/{ids[0]}", json={"new": 3, "fetched": 10})
    await signed_in.put(f"/career-source/result/{ids[1]}", json={"blocked": True})
    await signed_in.put(f"/career-source/result/{ids[2]}", json={"failed": 2, "error": "timeout"})

    discovery = (await status(signed_in))["discovery"]

    assert (discovery["companies"], discovery["ok"], discovery["blocked"], discovery["failed"]) == (
        3, 1, 1, 1,
    )  # fmt: skip
    assert discovery["newJobs"] == 3
    assert discovery["lastRunAt"] is not None


async def test_status_is_yours_alone(client: AsyncClient) -> None:
    await sign_up(client, "one@example.com")
    job_id = await make_job(client, "LLM Engineer", "R1")
    await score(client, job_id, 72)
    await client.post(f"/application/shortlist/{job_id}")

    await sign_up(client, "two@example.com")
    body = await status(client)

    assert body["badges"]["shortlisted"] == 0 and body["badges"]["keywordSelections"] == 0
    # The posting is shared; your match is not.
    assert body["jobs"] == {"total": 1, "unscored": 1, "analyzed": 0}
