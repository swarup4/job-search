"""The reads the Pipeline board is built from: counts per column, match summaries for
the cards on screen, and which job the keyword gate should open next."""

from __future__ import annotations

from httpx import AsyncClient


async def make_job(client: AsyncClient, title: str, ref: str) -> str:
    response = await client.post(
        "/job/createJob",
        json={
            "title": title,
            "company": "Acme",
            "location": "Bengaluru, India",
            "source": "career_page",
            "refId": ref,
        },
    )
    assert response.status_code == 201, response.text
    job_id = response.json()["id"]

    text = f"{title} — build RAG pipelines on AWS."
    captured = await client.post(
        "/job-description",
        json={
            "url": f"https://acme.example/jobs/{ref}",
            "pageTitle": title,
            "markdown": text,
            "region": "feed",
            "textLength": len(text),
        },
    )
    assert captured.status_code == 201, captured.text
    linked = await client.post(f"/job-description/link/{captured.json()['id']}/{job_id}")
    assert linked.status_code == 200, linked.text
    return job_id


async def score(
    client: AsyncClient, job_id: str, value: int, risks: list[dict] | None = None
) -> None:
    response = await client.post(
        "/match/writeMatch",
        json={
            "jobId": job_id,
            "score": value,
            "present": [{"label": "AWS"}],
            "missing": [
                {"key": "rag", "label": "RAG", "mentions": 1, "evidence": "build RAG pipelines"}
            ],
            "risks": risks or [],
            "modelName": "test",
        },
    )
    assert response.status_code == 201, response.text


async def test_counts_cover_every_column(signed_in: AsyncClient) -> None:
    first = await make_job(signed_in, "LLM Engineer", "R1")
    await make_job(signed_in, "GenAI Engineer", "R2")
    await signed_in.patch(f"/job/updateJob/{first}", json={"status": "reviewed"})

    counts = (await signed_in.get("/job/counts")).json()
    assert counts == {"new": 1, "reviewed": 1, "tailored": 0, "applied": 0, "archived": 0}


async def test_counts_need_a_token(client: AsyncClient) -> None:
    assert (await client.get("/job/counts")).status_code == 401


async def test_summaries_return_only_scored_jobs(signed_in: AsyncClient) -> None:
    scored = await make_job(signed_in, "LLM Engineer", "R1")
    unscored = await make_job(signed_in, "GenAI Engineer", "R2")
    await score(
        signed_in,
        scored,
        82,
        risks=[{"key": "seniority", "title": "Seniority mismatch", "detail": "Asks for 15 years"}],
    )

    rows = (
        await signed_in.get("/match/summaries", params=[("jobIds", scored), ("jobIds", unscored)])
    ).json()
    assert rows == [
        {"jobId": scored, "score": 82, "reviewState": "pending", "risk": "Seniority mismatch"}
    ]


async def test_pending_names_the_longest_waiting_job(signed_in: AsyncClient) -> None:
    empty = (await signed_in.get("/match/pending")).json()
    assert empty == {"keywordSelections": 0, "nextJobId": None}

    older = await make_job(signed_in, "LLM Engineer", "R1")
    newer = await make_job(signed_in, "GenAI Engineer", "R2")
    await score(signed_in, older, 70)
    await score(signed_in, newer, 90)

    pending = (await signed_in.get("/match/pending")).json()
    assert pending == {"keywordSelections": 2, "nextJobId": older}


async def test_analysis_details_can_be_written_to_a_job(signed_in: AsyncClient) -> None:
    job_id = await make_job(signed_in, "LLM Engineer", "R1")
    response = await signed_in.patch(
        f"/job/updateJob/{job_id}",
        json={"experienceBand": "6-10 years", "salaryText": "₹40–55 LPA", "workMode": "hybrid"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["experienceBand"] == "6-10 years"
    assert body["workMode"] == "hybrid"
    assert body["status"] == "new"


async def test_an_unknown_work_mode_is_refused(signed_in: AsyncClient) -> None:
    job_id = await make_job(signed_in, "LLM Engineer", "R1")
    response = await signed_in.patch(f"/job/updateJob/{job_id}", json={"workMode": "sometimes"})
    assert response.status_code == 422


async def test_the_shortlist_toggle_is_saved(signed_in: AsyncClient) -> None:
    job_id = await make_job(signed_in, "LLM Engineer", "R1")
    await signed_in.patch(f"/job/updateJob/{job_id}", json={"shortlisted": True})
    assert (await signed_in.get(f"/job/getJob/{job_id}")).json()["shortlisted"] is True

    await signed_in.patch(f"/job/updateJob/{job_id}", json={"shortlisted": False})
    assert (await signed_in.get(f"/job/getJob/{job_id}")).json()["shortlisted"] is False


async def test_details_join_the_description(signed_in: AsyncClient) -> None:
    job_id = await make_job(signed_in, "LLM Engineer", "R1")
    description_id = (await signed_in.get(f"/job-description/for-job/{job_id}")).json()["id"]
    await signed_in.put(
        f"/job-description/embedding/{description_id}", json={"embedding": [0.1] * 8}
    )

    response = await signed_in.get(f"/job/getJobDetails/{job_id}")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == job_id
    assert body["title"] == "LLM Engineer"
    assert body["description"]["id"] == description_id
    assert "build RAG pipelines" in body["description"]["jdText"]
    # Neither the vector nor the dedup hash leaves the server.
    assert "embedding" not in body["description"]
    assert "dedupHash" not in body


async def test_details_of_a_job_without_a_description(signed_in: AsyncClient) -> None:
    created = await signed_in.post(
        "/job/createJob",
        json={
            "title": "GenAI Engineer",
            "company": "Acme",
            "location": "Pune",
            "source": "career_page",
        },
    )
    body = (await signed_in.get(f"/job/getJobDetails/{created.json()['id']}")).json()
    assert body["title"] == "GenAI Engineer"
    assert body["description"] is None


async def test_details_of_an_unknown_job(signed_in: AsyncClient) -> None:
    response = await signed_in.get("/job/getJobDetails/0123456789abcdef01234567")
    assert response.status_code == 404
