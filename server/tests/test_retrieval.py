"""P6-01 to P6-03 — chunking the profile, and keeping the index honest.

`$vectorSearch` itself is not exercised here: it is an Atlas Search stage, not a
MongoDB one, and this suite is forced at a local server on purpose (see conftest).
What is checked is everything around it — that an edit re-chunks, that a vector
survives text that did not change and does not survive text that did, and that a
vector cannot be written onto somebody else's chunk.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from modules.resume_chunk.service import cosine_from_score

ROLE = {
    "title": "Senior Engineer",
    "company": "LTI",
    "start": "2021-04",
    "current": True,
    "bullets": [
        "Built a LangGraph multi-agent pipeline with tool orchestration",
        "Shipped a RAG service over MongoDB Atlas",
    ],
    "projects": [{"name": "Atlas migration", "bullets": ["Moved 40M documents with no downtime"]}],
}

SKILLS = {"name": "GenAI", "items": ["LangChain", "LangGraph", "RAG"]}


async def chunks(client: AsyncClient) -> list[dict]:
    response = await client.get("/resume-chunk")
    assert response.status_code == 200, response.text
    return response.json()


async def stats(client: AsyncClient) -> dict:
    response = await client.get("/resume-chunk/stats")
    assert response.status_code == 200, response.text
    return response.json()


async def embed(client: AsyncClient, chunk_ids: list[str]) -> int:
    """Stand in for the AI tier: any vector will do, nothing here reads it back."""
    response = await client.put(
        "/resume-chunk/embeddings",
        json={
            "embeddings": [{"chunkId": chunk_id, "embedding": [0.1] * 8} for chunk_id in chunk_ids]
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["stored"]


# --- P6-02: the profile becomes retrievable units ----------------------------


async def test_adding_a_role_chunks_it_bullet_by_bullet(signed_in: AsyncClient) -> None:
    """One vector for a whole role would average it into something that matches every
    job weakly, and the near-miss hint has to hand a span back to the user."""
    await signed_in.post("/profile/addExperience", json=ROLE)

    texts = [chunk["text"] for chunk in await chunks(signed_in)]

    assert "Senior Engineer at LTI" in texts
    assert "Shipped a RAG service over MongoDB Atlas" in texts
    assert "Moved 40M documents with no downtime" in texts


async def test_a_skill_group_becomes_one_chunk_per_skill(signed_in: AsyncClient) -> None:
    """Embedding "LangChain, LangGraph, RAG" as one span returns all three whenever a
    job asks for any one of them."""
    await signed_in.post("/profile/addSkill", json=SKILLS)

    skills = [chunk for chunk in await chunks(signed_in) if chunk["section"] == "skill"]

    assert sorted(chunk["text"] for chunk in skills) == ["LangChain", "LangGraph", "RAG"]
    assert {chunk["sourceRef"] for chunk in skills} == {"GenAI"}


async def test_a_bullet_repeated_across_roles_is_stored_once(signed_in: AsyncClient) -> None:
    """The same text twice is one vector's worth of meaning and two rows of noise in
    every result that returns it."""
    await signed_in.post("/profile/addExperience", json=ROLE)
    await signed_in.post("/profile/addExperience", json={**ROLE, "company": "Mphasis"})

    texts = [chunk["text"] for chunk in await chunks(signed_in)]

    assert texts.count("Shipped a RAG service over MongoDB Atlas") == 1
    assert "Senior Engineer at Mphasis" in texts


async def test_chunks_start_with_no_vector(signed_in: AsyncClient) -> None:
    """Chunking is free and embedding is not, so the server never pretends to have
    done the half it cannot do."""
    await signed_in.post("/profile/addSkill", json=SKILLS)

    assert all(chunk["embeddedAt"] is None for chunk in await chunks(signed_in))
    assert await stats(signed_in) == {
        "chunks": 3,
        "embedded": 0,
        "pending": 3,
        "lastIndexedAt": None,
    }


async def test_deleting_a_role_takes_its_chunks_with_it(signed_in: AsyncClient) -> None:
    response = await signed_in.post("/profile/addExperience", json=ROLE)
    entry_id = response.json()["id"]

    await signed_in.delete(f"/profile/deleteExperience/{entry_id}")

    assert await chunks(signed_in) == []


# --- P6-03: an edit must not leave retrievable stale text --------------------


async def test_an_untouched_bullet_keeps_its_vector(signed_in: AsyncClient) -> None:
    """Re-chunking on every edit is only affordable because it does not re-embed what
    did not change."""
    response = await signed_in.post("/profile/addExperience", json=ROLE)
    entry_id = response.json()["id"]
    await embed(signed_in, [chunk["id"] for chunk in await chunks(signed_in)])

    edited = {**ROLE, "bullets": [ROLE["bullets"][0], "Ran red-team prompt-injection testing"]}
    await signed_in.put(f"/profile/updateExperience/{entry_id}", json=edited)

    by_text = {chunk["text"]: chunk for chunk in await chunks(signed_in)}
    assert by_text[ROLE["bullets"][0]]["embeddedAt"] is not None


async def test_edited_text_is_not_retrievable_until_it_is_re_embedded(
    signed_in: AsyncClient,
) -> None:
    """The point of P6-03. A chunk with no vector cannot come back from a
    `$vectorSearch`, so the window between an edit and the next indexing run serves
    nothing rather than serving what the user just replaced."""
    response = await signed_in.post("/profile/addExperience", json=ROLE)
    entry_id = response.json()["id"]
    await embed(signed_in, [chunk["id"] for chunk in await chunks(signed_in)])

    edited = {**ROLE, "bullets": [ROLE["bullets"][0], "Ran red-team prompt-injection testing"]}
    await signed_in.put(f"/profile/updateExperience/{entry_id}", json=edited)

    by_text = {chunk["text"]: chunk for chunk in await chunks(signed_in)}
    assert ROLE["bullets"][1] not in by_text
    assert by_text["Ran red-team prompt-injection testing"]["embeddedAt"] is None


async def test_pending_lists_only_what_still_needs_a_vector(signed_in: AsyncClient) -> None:
    await signed_in.post("/profile/addSkill", json=SKILLS)
    first = (await chunks(signed_in))[0]

    await embed(signed_in, [first["id"]])

    pending = await signed_in.get("/resume-chunk/pending")
    assert [chunk["id"] for chunk in pending.json()] == [
        chunk["id"] for chunk in await chunks(signed_in) if chunk["id"] != first["id"]
    ]
    assert (await stats(signed_in))["embedded"] == 1


async def test_reindex_is_idempotent(signed_in: AsyncClient) -> None:
    """The panel's button, pressed twice, must not double the index or lose vectors."""
    await signed_in.post("/profile/addExperience", json=ROLE)
    await embed(signed_in, [chunk["id"] for chunk in await chunks(signed_in)])

    first = await signed_in.post("/profile/reindex")
    second = await signed_in.post("/profile/reindex")

    assert first.json() == second.json()
    assert second.json()["pending"] == 0


# --- writing a vector onto a chunk -------------------------------------------


async def test_a_vector_cannot_be_written_onto_another_users_chunk(
    signed_in: AsyncClient, client: AsyncClient
) -> None:
    """The one failure that would never surface on its own: a vector landing on
    somebody else's text makes their resume retrievable through your search."""
    await signed_in.post("/profile/addSkill", json=SKILLS)
    mine = (await chunks(signed_in))[0]["id"]

    other = await client.post(
        "/account/signup",
        json={"name": "Other", "email": "other@example.com", "password": "correct-horse"},
    )
    token = other.json()["accessToken"]

    response = await signed_in.put(
        "/resume-chunk/embeddings",
        json={"embeddings": [{"chunkId": mine, "embedding": [0.1] * 8}]},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422
    assert mine in response.json()["detail"]


async def test_a_batch_naming_a_chunk_that_no_longer_exists_is_refused(
    signed_in: AsyncClient,
) -> None:
    """A re-index between the AI tier reading the queue and writing the vectors. The
    whole batch is refused rather than partly applied, so the caller retries against
    the queue as it now is."""
    await signed_in.post("/profile/addSkill", json=SKILLS)
    stale = [chunk["id"] for chunk in await chunks(signed_in)]
    await signed_in.delete(
        f"/profile/deleteSkill/{(await signed_in.get('/profile/getSkills')).json()[0]['id']}"
    )

    response = await signed_in.put(
        "/resume-chunk/embeddings",
        json={"embeddings": [{"chunkId": chunk_id, "embedding": [0.1] * 8} for chunk_id in stale]},
    )

    assert response.status_code == 422


# --- the score Atlas actually returns ----------------------------------------


@pytest.mark.parametrize(
    ("score", "expected"),
    [(1.0, 1.0), (0.5, 0.0), (0.675, 0.35), (0.0, -1.0)],
)
def test_atlas_scores_are_converted_back_to_cosines(score: float, expected: float) -> None:
    """Atlas reports a cosine search as `(1 + cosine) / 2`. The AI tier's near-miss
    threshold is a real cosine calibrated in `rag/embeddings.py`, so 0.5 meaning
    "nothing in common" has to be undone before the two are ever compared."""
    assert cosine_from_score(score) == pytest.approx(expected)
