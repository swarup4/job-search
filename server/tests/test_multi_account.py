"""Two accounts on one database. `jobs` is a shared catalogue, so everything a user
does to a job has to be keyed by the user as well as the job.

The match and the tailored resume were unique on the job alone, which let only the
first account to reach a posting score or tailor it. These tests are that failure.
"""

from __future__ import annotations

from httpx import AsyncClient

JOB = {
    "title": "Platform Engineer",
    "company": "Acme",
    "location": "Bengaluru, India",
    "source": "linkedin",
}

JD_TEXT = "Run our Kubernetes clusters and write Terraform for the AWS estate."

MISSING = [
    {"key": "kubernetes", "label": "Kubernetes", "mentions": 2, "evidence": "Kubernetes clusters"},
    {"key": "terraform", "label": "Terraform", "mentions": 1, "evidence": "write Terraform"},
]


async def sign_up(client: AsyncClient, name: str) -> dict[str, str]:
    response = await client.post(
        "/account/signup",
        json={"name": name, "email": f"{name.lower()}@example.com", "password": "correct-horse"},
    )
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['accessToken']}"}


async def make_job(client: AsyncClient, headers: dict[str, str]) -> str:
    created = await client.post("/job/createJob", json=JOB, headers=headers)
    assert created.status_code == 201, created.text
    job_id = created.json()["id"]

    captured = await client.post(
        "/job-description",
        json={
            "url": "https://acme.example/jobs/platform-engineer",
            "pageTitle": "Platform Engineer at Acme",
            "markdown": JD_TEXT,
            "region": "main",
            "textLength": len(JD_TEXT),
        },
        headers=headers,
    )
    assert captured.status_code == 201, captured.text
    linked = await client.post(
        f"/job-description/link/{captured.json()['id']}/{job_id}", headers=headers
    )
    assert linked.status_code == 200, linked.text
    return job_id


async def score(client: AsyncClient, headers: dict[str, str], job_id: str, value: int) -> None:
    response = await client.post(
        "/match/writeMatch",
        json={"jobId": job_id, "score": value, "missing": MISSING, "promptVersion": 1},
        headers=headers,
    )
    assert response.status_code == 201, response.text


async def tailor(client: AsyncClient, headers: dict[str, str], job_id: str, tex: str) -> dict:
    selected = await client.post(
        f"/match/selection/{job_id}", json={"selectedKeys": ["kubernetes"]}, headers=headers
    )
    assert selected.status_code == 200, selected.text
    stored = await client.post(
        "/resume/storeResume",
        json={
            "jobId": job_id,
            "filePath": f"output/tailored/{job_id}.tex",
            "tex": tex,
            "incorporated": ["Kubernetes"],
            "promptVersion": 1,
        },
        headers=headers,
    )
    assert stored.status_code == 201, stored.text
    return stored.json()


async def test_two_accounts_can_each_score_the_same_job(client: AsyncClient) -> None:
    one, two = await sign_up(client, "One"), await sign_up(client, "Two")
    job_id = await make_job(client, one)

    await score(client, one, job_id, 40)
    await score(client, two, job_id, 75)

    first = (await client.get(f"/match/getMatch/{job_id}", headers=one)).json()
    second = (await client.get(f"/match/getMatch/{job_id}", headers=two)).json()
    assert (first["score"], second["score"]) == (40, 75)
    assert first["id"] != second["id"]


async def test_one_accounts_selection_does_not_open_the_others_gate(client: AsyncClient) -> None:
    one, two = await sign_up(client, "One"), await sign_up(client, "Two")
    job_id = await make_job(client, one)
    await score(client, one, job_id, 40)
    await score(client, two, job_id, 75)

    await client.post(
        f"/match/selection/{job_id}", json={"selectedKeys": ["kubernetes"]}, headers=one
    )

    theirs = (await client.get(f"/match/getMatch/{job_id}", headers=two)).json()
    assert theirs["review"]["state"] == "pending"
    assert theirs["review"]["selectedKeys"] == []


async def test_a_re_score_still_replaces_the_callers_own_match(client: AsyncClient) -> None:
    one = await sign_up(client, "One")
    job_id = await make_job(client, one)

    await score(client, one, job_id, 40)
    await score(client, one, job_id, 60)

    match = (await client.get(f"/match/getMatch/{job_id}", headers=one)).json()
    assert match["score"] == 60
    assert match["promptVersion"] == 1


async def test_two_accounts_can_each_tailor_the_same_job(client: AsyncClient) -> None:
    one, two = await sign_up(client, "One"), await sign_up(client, "Two")
    job_id = await make_job(client, one)
    await score(client, one, job_id, 40)
    await score(client, two, job_id, 75)

    first = await tailor(client, one, job_id, "one's resume\n")
    second = await tailor(client, two, job_id, "two's resume\n")

    # Versions count per account, so both are a first version.
    assert (first["version"], second["version"]) == (1, 1)
    read_one = (await client.get(f"/resume/getResume/{job_id}", headers=one)).json()
    read_two = (await client.get(f"/resume/getResume/{job_id}", headers=two)).json()
    assert (read_one["tex"], read_two["tex"]) == ("one's resume\n", "two's resume\n")


async def test_an_account_without_a_match_sees_none(client: AsyncClient) -> None:
    one, two = await sign_up(client, "One"), await sign_up(client, "Two")
    job_id = await make_job(client, one)
    await score(client, one, job_id, 40)

    assert (await client.get(f"/match/getMatch/{job_id}", headers=two)).status_code == 404
    assert (await client.get(f"/resume/getResume/{job_id}", headers=two)).status_code == 404
    unscored = (await client.get("/match/unscored", headers=two)).json()
    assert [job["id"] for job in unscored["jobs"]] == [job_id]
