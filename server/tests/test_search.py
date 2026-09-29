"""The Search screen's query: every field narrows, and text matches case-insensitively."""

from __future__ import annotations

from httpx import AsyncClient

from tests.test_board import score, sign_up, stage


async def add_job(
    client: AsyncClient,
    ref: str,
    title: str,
    company: str = "Acme",
    location: str = "Bengaluru, India",
    text: str | None = None,
    **fields: str,
) -> str:
    response = await client.post(
        "/job/createJob",
        json={
            "title": title,
            "company": company,
            "location": location,
            "source": "career_page",
            "refId": ref,
            **fields,
        },
    )
    assert response.status_code == 201, response.text
    job_id = response.json()["id"]
    if text is not None:
        captured = await client.post(
            "/job-description",
            json={
                "url": f"https://jobs.example/{ref}",
                "pageTitle": title,
                "markdown": text,
                "region": "feed",
                "textLength": len(text),
            },
        )
        await client.post(f"/job-description/link/{captured.json()['id']}/{job_id}")
    return job_id


async def found(client: AsyncClient, **params: object) -> list[str]:
    response = await client.post("/job/search", json=params)
    assert response.status_code == 200, response.text
    return [job["title"] for job in response.json()["jobs"]]


async def test_no_filters_returns_everything_newest_first(signed_in: AsyncClient) -> None:
    await add_job(signed_in, "R1", "LLM Engineer")
    await add_job(signed_in, "R2", "GenAI Lead")

    body = (await signed_in.post("/job/search", json={})).json()
    assert body["indexed"] == 2 and body["total"] == 2
    assert [job["title"] for job in body["jobs"]] == ["GenAI Lead", "LLM Engineer"]


async def test_text_fields_match_anywhere_ignoring_case(signed_in: AsyncClient) -> None:
    await add_job(signed_in, "R1", "LLM Engineer", company="Accenture", location="Pune")
    await add_job(signed_in, "R2", "Data Analyst", company="Capgemini", location="Bengaluru")

    assert await found(signed_in, company="accent") == ["LLM Engineer"]
    assert await found(signed_in, location="BENGAL") == ["Data Analyst"]
    assert await found(signed_in, title="analyst") == ["Data Analyst"]


async def test_keyword_searches_the_description(signed_in: AsyncClient) -> None:
    await add_job(signed_in, "R1", "Engineer", text="Build RAG pipelines on Kubernetes.")
    await add_job(signed_in, "R2", "Engineer II", text="Maintain Java services.")
    # A title alone is the Job title box's business, not the keyword's.
    await add_job(signed_in, "R3", "Kubernetes Admin")

    assert await found(signed_in, keywords=["kubernetes"]) == ["Engineer"]


async def test_every_keyword_must_appear(signed_in: AsyncClient) -> None:
    await add_job(signed_in, "R1", "Both", text="Python services on MongoDB Atlas.")
    await add_job(signed_in, "R2", "Python only", text="Python and PostgreSQL.")
    await add_job(signed_in, "R3", "Mongo only", text="Node.js with MongoDB.")

    assert await found(signed_in, keywords=["python", "mongodb"]) == ["Both"]
    assert sorted(await found(signed_in, keywords=["mongodb"])) == ["Both", "Mongo only"]


async def test_a_keyword_is_literal_not_a_pattern(signed_in: AsyncClient) -> None:
    await add_job(signed_in, "R1", "C++ Developer", text="Modern C++ and templates.")
    await add_job(signed_in, "R2", "C Developer", text="Embedded C on microcontrollers.")
    assert await found(signed_in, keywords=["c++"]) == ["C++ Developer"]


async def test_surrounding_spaces_are_ignored(signed_in: AsyncClient) -> None:
    await add_job(signed_in, "R1", "LLM Engineer", company="Accenture")
    await add_job(signed_in, "R2", "Data Analyst", company="Capgemini")
    assert await found(signed_in, company="  accenture ") == ["LLM Engineer"]
    assert sorted(await found(signed_in, keywords=["   "])) == ["Data Analyst", "LLM Engineer"]


async def test_posted_within_falls_back_to_when_it_was_found(signed_in: AsyncClient) -> None:
    await add_job(signed_in, "R1", "Old Posting", postedAt="2020-01-01T00:00:00Z")
    await add_job(signed_in, "R2", "Undated")
    assert await found(signed_in, postedWithin=7) == ["Undated"]


async def test_pages_share_one_total(signed_in: AsyncClient) -> None:
    for n in range(5):
        await add_job(signed_in, f"R{n}", f"Role {n}")

    first = (await signed_in.post("/job/search", json={"limit": 2})).json()
    second = (await signed_in.post("/job/search", json={"limit": 2, "skip": 2})).json()
    assert first["total"] == second["total"] == 5
    assert {job["id"] for job in first["jobs"]}.isdisjoint(job["id"] for job in second["jobs"])


async def test_each_row_carries_your_score_and_shortlist(signed_in: AsyncClient) -> None:
    scored = await add_job(signed_in, "R1", "Scored")
    await add_job(signed_in, "R2", "Untouched")
    await score(signed_in, scored, 82)
    await signed_in.post(f"/application/shortlist/{scored}")

    rows = {
        row["title"]: row for row in (await signed_in.post("/job/search", json={})).json()["jobs"]
    }
    assert rows["Scored"]["score"] == 82
    assert rows["Scored"]["presentCount"] == 1 and rows["Scored"]["missingCount"] == 1
    assert rows["Scored"]["shortlisted"] is True
    assert rows["Untouched"]["score"] is None and rows["Untouched"]["shortlisted"] is False


async def test_another_accounts_score_and_shortlist_stay_theirs(client: AsyncClient) -> None:
    await sign_up(client, "one@example.com")
    job_id = await add_job(client, "R1", "LLM Engineer")
    await score(client, job_id, 90)
    await client.post(f"/application/shortlist/{job_id}")

    await sign_up(client, "two@example.com")
    [row] = (await client.post("/job/search", json={})).json()["jobs"]
    assert row["score"] is None and row["shortlisted"] is False


async def test_a_withdrawn_application_is_not_shortlisted(signed_in: AsyncClient) -> None:
    job_id = await add_job(signed_in, "R1", "LLM Engineer")
    await signed_in.post(f"/application/shortlist/{job_id}")
    await stage(signed_in, job_id)
    await signed_in.delete(f"/application/shortlist/{job_id}")

    [row] = (await signed_in.post("/job/search", json={})).json()["jobs"]
    assert row["shortlisted"] is False


async def test_search_needs_a_token(client: AsyncClient) -> None:
    assert (await client.post("/job/search", json={})).status_code == 401
