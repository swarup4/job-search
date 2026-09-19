"""P5-13 — the no-fabrication guardrail, where the server enforces it.

NFR-8 requires every keyword in a tailored resume to trace back to something the
user explicitly ticked, and FR-7.3 requires the keyword gate to be answered before
any tailoring happens at all. Both are checked here against the real endpoints,
because a guardrail with no test is an intention.
"""

from __future__ import annotations

from httpx import AsyncClient

JOB = {
    "title": "Platform Engineer",
    "company": "Acme",
    "location": "Bengaluru, India",
    "source": "linkedin",
    "requirements": ["kubernetes", "terraform", "aws"],
}

JD_TEXT = "Run our Kubernetes clusters and write Terraform for the AWS estate."

DESCRIPTION = {
    "url": "https://acme.example/jobs/platform-engineer",
    "pageTitle": "Platform Engineer at Acme",
    "markdown": JD_TEXT,
    "region": "main",
    "textLength": len(JD_TEXT),
}

MISSING = [
    {
        "key": "kubernetes",
        "label": "Kubernetes",
        "mentions": 2,
        "evidence": "Run our Kubernetes clusters",
    },
    {"key": "terraform", "label": "Terraform", "mentions": 1, "evidence": "write Terraform"},
]


async def make_job(client: AsyncClient) -> str:
    """A job and the description it was parsed from — two collections now, so the
    prose has to be captured and linked rather than posted with the listing."""
    response = await client.post("/job/createJob", json=JOB)
    assert response.status_code == 201, response.text
    job_id = response.json()["id"]

    captured = await client.post("/job-description", json=DESCRIPTION)
    assert captured.status_code == 201, captured.text
    description_id = captured.json()["id"]

    linked = await client.post(f"/job-description/link/{description_id}/{job_id}")
    assert linked.status_code == 200, linked.text
    return job_id


async def make_match(client: AsyncClient, job_id: str) -> None:
    response = await client.post(
        "/match/writeMatch",
        json={
            "jobId": job_id,
            "score": 50,
            "present": [{"label": "AWS"}],
            "missing": MISSING,
            "risks": [],
            "modelName": "huggingface/Qwen/Qwen3-32B:nscale",
        },
    )
    assert response.status_code == 201, response.text


def resume(job_id: str, incorporated: list[str]) -> dict:
    return {
        "jobId": job_id,
        "filePath": f"output/tailored/{job_id}.tex",
        "incorporated": incorporated,
        "declined": [],
        "changes": [],
    }


# --- the gate ----------------------------------------------------------------


async def test_a_new_match_starts_pending_with_nothing_selected(signed_in: AsyncClient) -> None:
    job_id = await make_job(signed_in)
    await make_match(signed_in, job_id)

    review = (await signed_in.get(f"/match/getMatch/{job_id}")).json()["review"]

    assert review["state"] == "pending"
    assert review["selectedKeys"] == []


async def test_a_resume_cannot_be_stored_before_the_gate_is_answered(
    signed_in: AsyncClient,
) -> None:
    job_id = await make_job(signed_in)
    await make_match(signed_in, job_id)

    response = await signed_in.post("/resume/storeResume", json=resume(job_id, []))

    assert response.status_code == 409
    assert "not a completed keyword selection" in response.json()["detail"]


async def test_skipping_the_job_is_not_a_selection(signed_in: AsyncClient) -> None:
    job_id = await make_job(signed_in)
    await make_match(signed_in, job_id)
    await signed_in.post(f"/match/selection/{job_id}", json={"selectedKeys": [], "skip": True})

    response = await signed_in.post("/resume/storeResume", json=resume(job_id, []))

    assert response.status_code == 409


async def test_a_keyword_the_match_never_offered_cannot_be_selected(signed_in: AsyncClient) -> None:
    job_id = await make_job(signed_in)
    await make_match(signed_in, job_id)

    response = await signed_in.post(
        f"/match/selection/{job_id}", json={"selectedKeys": ["golang"], "skip": False}
    )

    assert response.status_code == 422
    assert "not in this match's missing list" in response.json()["detail"]


async def test_re_scoring_a_job_reopens_the_gate(signed_in: AsyncClient) -> None:
    """A re-score replaces the findings, so an approval given against the old
    keywords must not carry over to the new ones."""
    job_id = await make_job(signed_in)
    await make_match(signed_in, job_id)
    await signed_in.post(
        f"/match/selection/{job_id}", json={"selectedKeys": ["kubernetes"], "skip": False}
    )

    await make_match(signed_in, job_id)
    review = (await signed_in.get(f"/match/getMatch/{job_id}")).json()["review"]

    assert review["state"] == "pending"
    assert review["selectedKeys"] == []


# --- the fabrication check ---------------------------------------------------


async def test_a_resume_incorporating_an_unselected_keyword_is_refused(
    signed_in: AsyncClient,
) -> None:
    job_id = await make_job(signed_in)
    await make_match(signed_in, job_id)
    await signed_in.post(
        f"/match/selection/{job_id}", json={"selectedKeys": ["kubernetes"], "skip": False}
    )

    response = await signed_in.post(
        "/resume/storeResume", json=resume(job_id, ["Kubernetes", "Terraform"])
    )

    assert response.status_code == 422
    assert "Terraform" in response.json()["detail"]
    assert (await signed_in.get(f"/resume/getResume/{job_id}")).status_code == 404


async def test_incorporating_fewer_keywords_than_were_ticked_is_allowed(
    signed_in: AsyncClient,
) -> None:
    """A selected keyword with no honest place is left out. That is the correct
    outcome, not a failure — so storing a subset must not be refused."""
    job_id = await make_job(signed_in)
    await make_match(signed_in, job_id)
    await signed_in.post(
        f"/match/selection/{job_id}",
        json={"selectedKeys": ["kubernetes", "terraform"], "skip": False},
    )

    response = await signed_in.post("/resume/storeResume", json=resume(job_id, ["Kubernetes"]))

    assert response.status_code == 201, response.text
    assert response.json()["incorporated"] == ["Kubernetes"]


async def test_the_stored_resume_records_the_selection_it_was_built_from(
    signed_in: AsyncClient,
) -> None:
    job_id = await make_job(signed_in)
    await make_match(signed_in, job_id)
    await signed_in.post(
        f"/match/selection/{job_id}", json={"selectedKeys": ["kubernetes"], "skip": False}
    )

    stored = (
        await signed_in.post("/resume/storeResume", json=resume(job_id, ["Kubernetes"]))
    ).json()

    assert stored["selectedKeys"] == ["kubernetes"]
    assert stored["version"] == 1


async def test_each_tailoring_run_is_a_new_version(signed_in: AsyncClient) -> None:
    job_id = await make_job(signed_in)
    await make_match(signed_in, job_id)
    await signed_in.post(
        f"/match/selection/{job_id}", json={"selectedKeys": ["kubernetes"], "skip": False}
    )

    await signed_in.post("/resume/storeResume", json=resume(job_id, ["Kubernetes"]))
    second = await signed_in.post("/resume/storeResume", json=resume(job_id, ["Kubernetes"]))

    assert second.json()["version"] == 2
    assert len((await signed_in.get(f"/resume/versions/{job_id}")).json()) == 2


# --- what the AI tier is allowed to read -------------------------------------


async def test_the_jd_endpoint_carries_the_prose_the_list_endpoint_withholds(
    signed_in: AsyncClient,
) -> None:
    job_id = await make_job(signed_in)

    listed = (await signed_in.get(f"/job/getJob/{job_id}")).json()
    described = (await signed_in.get(f"/job-description/for-job/{job_id}")).json()

    assert "jdText" not in listed
    assert described["jdText"] == JD_TEXT


async def test_a_posting_is_shared_across_accounts(client: AsyncClient) -> None:
    """`jobs` and `job_descriptions` are a shared catalogue, not per-account data.

    This asserted a 404 until 2026-09-19, when `userId` was removed from both: a
    posting is a public advert, and what is private about it — the match, the
    tailored resume, the application — lives in collections that are still scoped.
    Kept as the record of that reversal of `P1-07`, so a 404 here reads as a
    regression rather than as the guarantee it used to be."""
    first = await client.post(
        "/account/signup",
        json={"name": "One", "email": "one@example.com", "password": "correct-horse"},
    )
    client.headers["Authorization"] = f"Bearer {first.json()['accessToken']}"
    job_id = await make_job(client)

    second = await client.post(
        "/account/signup",
        json={"name": "Two", "email": "two@example.com", "password": "correct-horse"},
    )
    client.headers["Authorization"] = f"Bearer {second.json()['accessToken']}"

    response = await client.get(f"/job-description/for-job/{job_id}")
    assert response.status_code == 200, response.text
    assert response.json()["jdText"] == JD_TEXT


async def test_the_jd_endpoint_still_needs_a_token(client: AsyncClient) -> None:
    assert (
        await client.get("/job-description/for-job/000000000000000000000000")
    ).status_code == 401
