"""The reads the Pipeline board is built from: counts per column, match summaries for
the cards on screen, which job the keyword gate should open next — and the shortlist,
which is the user's own application row, never a field on the shared job."""

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


async def stage(client: AsyncClient, job_id: str) -> None:
    response = await client.post(
        "/application/stageApplication",
        json={"jobId": job_id, "resumeId": "0" * 24, "texPath": "out/resume.tex"},
    )
    assert response.status_code == 201, response.text


async def sign_up(client: AsyncClient, email: str) -> None:
    response = await client.post(
        "/account/signup", json={"name": email, "email": email, "password": "correct-horse"}
    )
    client.headers["Authorization"] = f"Bearer {response.json()['accessToken']}"


async def test_counts_cover_every_column(signed_in: AsyncClient) -> None:
    first = await make_job(signed_in, "LLM Engineer", "R1")
    second = await make_job(signed_in, "GenAI Engineer", "R2")
    await make_job(signed_in, "ML Engineer", "R3")
    await signed_in.post(f"/application/shortlist/{first}")
    await stage(signed_in, second)

    counts = (await signed_in.get("/application/counts")).json()
    assert counts == {"new": 1, "shortlisted": 1, "staged": 1, "applied": 0, "interview": 0}


async def test_counts_need_a_token(client: AsyncClient) -> None:
    assert (await client.get("/application/counts")).status_code == 401


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
        {
            "jobId": scored,
            "score": 82,
            "reviewState": "pending",
            "risk": "Seniority mismatch",
            "riskCount": 1,
            "presentCount": 1,
            "missingCount": 1,
        }
    ]


async def test_badges_name_the_longest_waiting_job(signed_in: AsyncClient) -> None:
    empty = (await signed_in.get("/application/badges")).json()
    assert empty == {"keywordSelections": 0, "nextJobId": None, "staged": 0, "shortlisted": 0}

    older = await make_job(signed_in, "LLM Engineer", "R1")
    newer = await make_job(signed_in, "GenAI Engineer", "R2")
    await score(signed_in, older, 70)
    await score(signed_in, newer, 90)

    badges = (await signed_in.get("/application/badges")).json()
    assert badges["keywordSelections"] == 2
    assert badges["nextJobId"] == older


async def test_badges_count_staged_and_shortlisted(signed_in: AsyncClient) -> None:
    shortlisted = await make_job(signed_in, "LLM Engineer", "R1")
    staged = await make_job(signed_in, "GenAI Engineer", "R2")
    await signed_in.post(f"/application/shortlist/{shortlisted}")
    await stage(signed_in, staged)

    badges = (await signed_in.get("/application/badges")).json()
    assert badges["shortlisted"] == 1 and badges["staged"] == 1


async def test_badges_need_a_token(client: AsyncClient) -> None:
    assert (await client.get("/application/badges")).status_code == 401


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


async def test_an_unknown_work_mode_is_refused(signed_in: AsyncClient) -> None:
    job_id = await make_job(signed_in, "LLM Engineer", "R1")
    response = await signed_in.patch(f"/job/updateJob/{job_id}", json={"workMode": "sometimes"})
    assert response.status_code == 422


async def test_shortlisting_creates_one_application(signed_in: AsyncClient) -> None:
    job_id = await make_job(signed_in, "LLM Engineer", "R1")
    first = await signed_in.post(f"/application/shortlist/{job_id}")
    assert first.status_code == 200, first.text
    assert first.json()["status"] == "shortlisted"
    assert first.json()["resumeId"] is None

    again = await signed_in.post(f"/application/shortlist/{job_id}")
    assert again.json()["id"] == first.json()["id"]
    assert len((await signed_in.get("/application")).json()) == 1


async def test_shortlisting_leaves_the_shared_job_alone(signed_in: AsyncClient) -> None:
    job_id = await make_job(signed_in, "LLM Engineer", "R1")
    before = (await signed_in.get(f"/job/getJob/{job_id}")).json()
    await signed_in.post(f"/application/shortlist/{job_id}")
    assert (await signed_in.get(f"/job/getJob/{job_id}")).json() == before


async def test_another_account_still_sees_the_job_as_new(client: AsyncClient) -> None:
    await sign_up(client, "one@example.com")
    job_id = await make_job(client, "LLM Engineer", "R1")
    await client.post(f"/application/shortlist/{job_id}")
    assert (await client.get("/application/unstarted")).json() == []

    await sign_up(client, "two@example.com")
    assert [job["id"] for job in (await client.get("/application/unstarted")).json()] == [job_id]
    assert (await client.get("/application/counts")).json()["shortlisted"] == 0


async def test_unshortlisting_an_untouched_job_returns_it_to_new(signed_in: AsyncClient) -> None:
    job_id = await make_job(signed_in, "LLM Engineer", "R1")
    await signed_in.post(f"/application/shortlist/{job_id}")

    response = await signed_in.delete(f"/application/shortlist/{job_id}")
    assert response.status_code == 200, response.text
    assert response.json() is None
    assert (await signed_in.get(f"/application/for-job/{job_id}")).json() is None
    assert (await signed_in.get("/application/counts")).json()["new"] == 1


async def test_unshortlisting_after_tailoring_withdraws(signed_in: AsyncClient) -> None:
    job_id = await make_job(signed_in, "LLM Engineer", "R1")
    await signed_in.post(f"/application/shortlist/{job_id}")
    await stage(signed_in, job_id)

    response = await signed_in.delete(f"/application/shortlist/{job_id}")
    assert response.json()["status"] == "withdrawn"

    back = await signed_in.post(f"/application/shortlist/{job_id}")
    assert back.json()["status"] == "shortlisted"


async def test_a_submitted_application_cannot_be_unshortlisted(signed_in: AsyncClient) -> None:
    job_id = await make_job(signed_in, "LLM Engineer", "R1")
    await stage(signed_in, job_id)
    application = (await signed_in.get(f"/application/for-job/{job_id}")).json()
    await signed_in.patch(
        f"/application/status/{application['id']}",
        json={"status": "applied", "confirmedByUser": True},
    )

    assert (await signed_in.delete(f"/application/shortlist/{job_id}")).status_code == 409


async def test_tailoring_an_unshortlisted_job_stages_its_row(signed_in: AsyncClient) -> None:
    job_id = await make_job(signed_in, "LLM Engineer", "R1")
    await stage(signed_in, job_id)
    await stage(signed_in, job_id)

    rows = (await signed_in.get("/application")).json()
    assert [row["status"] for row in rows] == ["staged"]
    assert rows[0]["stagedAt"] is not None


async def test_shortlisting_an_unknown_job_is_refused(signed_in: AsyncClient) -> None:
    response = await signed_in.post(f"/application/shortlist/{'0' * 24}")
    assert response.status_code == 404


async def test_scoring_does_not_move_a_job(signed_in: AsyncClient) -> None:
    job_id = await make_job(signed_in, "LLM Engineer", "R1")
    await score(signed_in, job_id, 80)
    assert (await signed_in.get("/application/counts")).json()["new"] == 1


async def test_unscored_lists_jobs_without_a_match(signed_in: AsyncClient) -> None:
    scored = await make_job(signed_in, "LLM Engineer", "R1")
    unscored = await make_job(signed_in, "GenAI Engineer", "R2")
    await score(signed_in, scored, 80)

    body = (await signed_in.get("/match/unscored", params={"limit": 5})).json()
    assert body["total"] == 1
    assert [job["id"] for job in body["jobs"]] == [unscored]

    assert (await signed_in.get("/match/unscored", params={"limit": 0})).json()["jobs"] == []


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


async def test_a_description_says_whether_it_is_embedded(signed_in: AsyncClient) -> None:
    job_id = await make_job(signed_in, "LLM Engineer", "R1")
    description = (await signed_in.get(f"/job-description/for-job/{job_id}")).json()
    assert description["hasEmbedding"] is False
    assert "embedding" not in description

    await signed_in.put(
        f"/job-description/embedding/{description['id']}", json={"embedding": [0.1] * 8}
    )
    assert (await signed_in.get(f"/job-description/for-job/{job_id}")).json()["hasEmbedding"]
    assert (await signed_in.get(f"/job-description/{description['id']}")).json()["hasEmbedding"]
