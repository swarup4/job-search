"""The reads the Pipeline board is built from: counts per column, match headlines for
the cards on screen, which job the keyword gate should open next — and the shortlist,
which is the user's own application row, never a field on the shared job."""

from __future__ import annotations

from beanie import PydanticObjectId
from httpx import AsyncClient

from modules.application import ApplicationStage, stage_application
from modules.application.service import get_for_job


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


async def user_id(client: AsyncClient) -> PydanticObjectId:
    return PydanticObjectId((await client.get("/account/getAccount")).json()["id"])


async def stage(client: AsyncClient, job_id: str) -> None:
    """What storing a tailored resume does, without a match and a resume to store."""
    await stage_application(
        await user_id(client),
        ApplicationStage(
            jobId=PydanticObjectId(job_id), resumeId=PydanticObjectId("0" * 24),
            texPath="out/resume.tex",
        ),
    )  # fmt: skip


async def application_for(client: AsyncClient, job_id: str) -> dict | None:
    """Your application row for a job, as the API would render it; None when there is none."""
    row = await get_for_job(await user_id(client), PydanticObjectId(job_id))
    return None if row is None else {**row.model_dump(mode="json"), "id": str(row.id)}


async def pipeline(client: AsyncClient) -> dict:
    return (await client.get("/status")).json()["pipeline"]


async def new_ids(client: AsyncClient) -> list[str]:
    cards = (await client.get("/application/board/new", params={"limit": 50})).json()
    return [card["id"] for card in cards]


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

    assert await pipeline(signed_in) == {
        "new": 1, "shortlisted": 1, "staged": 1, "applied": 0, "interview": 0,
    }  # fmt: skip


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
    assert await new_ids(client) == []

    await sign_up(client, "two@example.com")
    assert await new_ids(client) == [job_id]
    assert (await pipeline(client))["shortlisted"] == 0


async def test_unshortlisting_an_untouched_job_returns_it_to_new(signed_in: AsyncClient) -> None:
    job_id = await make_job(signed_in, "LLM Engineer", "R1")
    await signed_in.post(f"/application/shortlist/{job_id}")

    response = await signed_in.delete(f"/application/shortlist/{job_id}")
    assert response.status_code == 200, response.text
    assert response.json() is None
    assert await application_for(signed_in, job_id) is None
    assert (await pipeline(signed_in))["new"] == 1


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
    application = await application_for(signed_in, job_id)
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
    assert (await pipeline(signed_in))["new"] == 1


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


async def test_the_board_is_one_read(signed_in: AsyncClient) -> None:
    """Every column's first cards and total, your match joined in."""
    new = await make_job(signed_in, "Fresh Role", "R1")
    reviewed = await make_job(signed_in, "LLM Engineer", "R2")
    tailored = await make_job(signed_in, "GenAI Engineer", "R3")
    await score(
        signed_in, reviewed, 72, risks=[{"key": "yrs", "title": "Years gap", "detail": "x"}]
    )
    await signed_in.post(f"/application/shortlist/{reviewed}")
    await stage(signed_in, tailored)

    board = (await signed_in.get("/application/board")).json()

    columns = board["columns"]
    assert {key: column["count"] for key, column in columns.items()} == {
        "new": 1, "shortlisted": 1, "staged": 1, "applied": 0, "interview": 0,
    }  # fmt: skip
    assert set(columns) == {"new", "shortlisted", "staged", "applied", "interview"}
    assert [card["id"] for card in columns["new"]["cards"]] == [new]
    assert columns["new"]["cards"][0]["score"] is None
    card = columns["shortlisted"]["cards"][0]
    assert (card["id"], card["score"], card["reviewState"], card["risk"]) == (
        reviewed,
        72,
        "pending",
        "Years gap",
    )
    assert columns["staged"]["cards"][0]["texPath"] == "out/resume.tex"
    assert columns["applied"] == {"count": 0, "cards": []}


async def test_show_more_pages_through_a_column(signed_in: AsyncClient) -> None:
    ids = [await make_job(signed_in, f"Role {n}", f"R{n}") for n in range(3)]

    first = (await signed_in.get("/application/board", params={"limit": 2})).json()
    more = (await signed_in.get("/application/board/new", params={"skip": 2, "limit": 2})).json()

    shown = [card["id"] for card in first["columns"]["new"]["cards"]] + [c["id"] for c in more]
    assert sorted(shown) == sorted(ids)
    assert len(more) == 1


async def test_the_board_is_yours_alone(client: AsyncClient) -> None:
    await sign_up(client, "one@example.com")
    job_id = await make_job(client, "LLM Engineer", "R1")
    await score(client, job_id, 72)
    await client.post(f"/application/shortlist/{job_id}")

    await sign_up(client, "two@example.com")
    board = (await client.get("/application/board")).json()

    assert board["columns"]["shortlisted"]["count"] == 0
    assert board["columns"]["new"]["cards"][0]["score"] is None


async def test_an_unknown_column_is_refused(signed_in: AsyncClient) -> None:
    assert (await signed_in.get("/application/board/archived")).status_code == 422


async def test_the_shortlist_joins_each_job_and_your_match(signed_in: AsyncClient) -> None:
    """One request for the Shortlist screen, not one per job."""
    scored = await make_job(signed_in, "LLM Engineer", "R1")
    unscored = await make_job(signed_in, "GenAI Engineer", "R2")
    await score(signed_in, scored, 72, risks=[{"key": "yrs", "title": "Years", "detail": "x"}])
    await signed_in.post(f"/application/shortlist/{scored}")
    await signed_in.post(f"/application/shortlist/{unscored}")

    rows = (await signed_in.get("/application/shortlist")).json()

    # Newest shortlisted first.
    assert [row["id"] for row in rows] == [unscored, scored]
    assert rows[0]["score"] is None and rows[0]["missingCount"] == 0
    assert rows[1]["title"] == "LLM Engineer"
    assert (
        rows[1]["score"],
        rows[1]["riskCount"],
        rows[1]["presentCount"],
        rows[1]["missingCount"],
    ) == (72, 1, 1, 1)


async def test_the_shortlist_leaves_out_staged_jobs(signed_in: AsyncClient) -> None:
    job_id = await make_job(signed_in, "LLM Engineer", "R1")
    await signed_in.post(f"/application/shortlist/{job_id}")
    await stage(signed_in, job_id)

    assert (await signed_in.get("/application/shortlist")).json() == []


async def test_the_shortlist_is_yours_alone(client: AsyncClient) -> None:
    await sign_up(client, "one@example.com")
    job_id = await make_job(client, "LLM Engineer", "R1")
    await score(client, job_id, 72)
    await client.post(f"/application/shortlist/{job_id}")

    await sign_up(client, "two@example.com")

    assert (await client.get("/application/shortlist")).json() == []


async def test_details_carry_your_match_and_shortlist(signed_in: AsyncClient) -> None:
    """One request for the details page instead of three."""
    job_id = await make_job(signed_in, "LLM Engineer", "R1")
    before = (await signed_in.get(f"/job/getJobDetails/{job_id}")).json()
    assert before["match"] is None and before["shortlisted"] is False

    await score(signed_in, job_id, 72)
    await signed_in.post(f"/application/shortlist/{job_id}")
    body = (await signed_in.get(f"/job/getJobDetails/{job_id}")).json()

    assert body["shortlisted"] is True
    assert body["match"]["score"] == 72
    assert body["match"]["missing"][0]["label"] == "RAG"
    assert body["match"]["review"]["state"] == "pending"
    assert body["match"]["id"] == (await signed_in.get(f"/match/getMatch/{job_id}")).json()["id"]
    assert "userId" not in body["match"]


async def test_details_show_only_your_own_match_and_shortlist(client: AsyncClient) -> None:
    await sign_up(client, "one@example.com")
    job_id = await make_job(client, "LLM Engineer", "R1")
    await score(client, job_id, 72)
    await client.post(f"/application/shortlist/{job_id}")

    await sign_up(client, "two@example.com")
    body = (await client.get(f"/job/getJobDetails/{job_id}")).json()

    assert body["match"] is None
    assert body["shortlisted"] is False


async def test_a_withdrawn_application_is_not_shortlisted(signed_in: AsyncClient) -> None:
    job_id = await make_job(signed_in, "LLM Engineer", "R1")
    await signed_in.post(f"/application/shortlist/{job_id}")
    await stage(signed_in, job_id)
    await signed_in.delete(f"/application/shortlist/{job_id}")

    body = (await signed_in.get(f"/job/getJobDetails/{job_id}")).json()

    assert body["shortlisted"] is False


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
