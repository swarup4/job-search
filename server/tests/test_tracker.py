"""The Applications screen's one read: shortlisted, staged and submitted applications,
each with its job joined, and nothing that was shortlisted and then undone."""

from __future__ import annotations

from httpx import AsyncClient

from tests.test_board import application_for, make_job, sign_up, stage


async def submit(client: AsyncClient, job_id: str, note: str | None = None) -> None:
    await stage(client, job_id)
    application = await application_for(client, job_id)
    response = await client.patch(
        f"/application/status/{application['id']}",
        json={"status": "applied", "confirmedByUser": True, "note": note},
    )
    assert response.status_code == 200, response.text


async def test_staged_and_submitted_arrive_with_their_jobs(signed_in: AsyncClient) -> None:
    staged = await make_job(signed_in, "LLM Engineer", "R1")
    applied = await make_job(signed_in, "GenAI Lead", "R2")
    await stage(signed_in, staged)
    await submit(signed_in, applied, note="Submitted from the extension")

    body = (await signed_in.get("/application/tracker")).json()
    [waiting] = body["staged"]
    assert waiting["title"] == "LLM Engineer"
    assert waiting["company"] == "Acme" and waiting["location"] == "Bengaluru, India"
    assert waiting["texPath"] == "out/resume.tex"

    [sent] = body["submitted"]
    assert sent["title"] == "GenAI Lead" and sent["status"] == "applied"
    assert sent["submittedAt"] is not None and sent["followUpDueAt"] is not None
    assert sent["lastActivityNote"] == "Submitted from the extension"


async def test_a_shortlisted_job_is_listed_first(signed_in: AsyncClient) -> None:
    job_id = await make_job(signed_in, "LLM Engineer", "R1")
    await signed_in.post(f"/application/shortlist/{job_id}")

    body = (await signed_in.get("/application/tracker")).json()
    [row] = body["shortlisted"]
    assert row["title"] == "LLM Engineer" and row["shortlistedAt"] is not None
    assert body["staged"] == [] and body["submitted"] == []


async def test_a_shortlist_undone_before_sending_is_left_out(signed_in: AsyncClient) -> None:
    job_id = await make_job(signed_in, "GenAI Lead", "R2")
    # Staged, then taken off the shortlist before it was ever sent: withdrawn, unsubmitted.
    await signed_in.post(f"/application/shortlist/{job_id}")
    await stage(signed_in, job_id)
    await signed_in.delete(f"/application/shortlist/{job_id}")

    body = (await signed_in.get("/application/tracker")).json()
    assert body == {"shortlisted": [], "staged": [], "submitted": []}


async def test_a_withdrawal_after_submitting_stays_listed(signed_in: AsyncClient) -> None:
    job_id = await make_job(signed_in, "LLM Engineer", "R1")
    await submit(signed_in, job_id)
    application = await application_for(signed_in, job_id)
    await signed_in.patch(f"/application/status/{application['id']}", json={"status": "withdrawn"})

    [row] = (await signed_in.get("/application/tracker")).json()["submitted"]
    assert row["status"] == "withdrawn"


async def test_the_fill_report_is_counted(signed_in: AsyncClient) -> None:
    job_id = await make_job(signed_in, "LLM Engineer", "R1")
    await stage(signed_in, job_id)
    application = await application_for(signed_in, job_id)
    await signed_in.post(
        f"/application/fill/{application['id']}",
        json={
            "fieldsFilled": [
                {"selector": "#name", "label": "Name", "value": "Test", "source": "profile"},
                {"selector": "#email", "label": "Email", "value": "t@x.io", "source": "profile"},
            ],
            "screeningAnswers": [
                {"question": "Notice period?", "answer": "30 days"},
                {"question": "Why us?"},
            ],
        },
    )

    [row] = (await signed_in.get("/application/tracker")).json()["staged"]
    assert row["fieldsFilled"] == 2 and row["needsAnswer"] == 1


async def test_another_accounts_applications_stay_theirs(client: AsyncClient) -> None:
    await sign_up(client, "one@example.com")
    job_id = await make_job(client, "LLM Engineer", "R1")
    await submit(client, job_id)

    await sign_up(client, "two@example.com")
    body = (await client.get("/application/tracker")).json()
    assert body == {"shortlisted": [], "staged": [], "submitted": []}


async def test_the_tracker_needs_a_token(client: AsyncClient) -> None:
    assert (await client.get("/application/tracker")).status_code == 401
