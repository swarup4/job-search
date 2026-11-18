"""P6-01 to P6-03 — chunking the profile, and keeping the index honest — and the
search over it (OS-01).

The search is an exact cosine in this process, so unlike the Atlas stage it replaced it
can be tested here: that results come back best first, that one user's query never
reaches another user's chunks, and that a chunk with no vector, or one embedded by a
different model, is left out. The ranking itself is a pure function and its tests need
no database.

Around it: that an edit re-chunks, that a vector survives text that did not change and
does not survive text that did, and that a vector cannot be written onto somebody
else's chunk.
"""

from __future__ import annotations

import pytest
from beanie import PydanticObjectId
from httpx import AsyncClient

from modules.resume_chunk import ResumeChunk
from modules.resume_chunk.models import ResumeChunkRead
from modules.resume_chunk.service import cosine, rank

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
    """Your chunks in order, as the API renders them — read from the store, since no
    screen lists them."""
    account = PydanticObjectId((await client.get("/account/getAccount")).json()["id"])
    rows = (
        await ResumeChunk.find(ResumeChunk.userId == account).sort(+ResumeChunk.ordinal).to_list()
    )
    return [
        ResumeChunkRead.model_validate(row, from_attributes=True).model_dump(mode="json")
        for row in rows
    ]


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
    search, so the window between an edit and the next indexing run serves
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
        f"/profile/deleteSkill/{(await signed_in.get('/profile/getProfile')).json()['skill'][0]['id']}"
    )

    response = await signed_in.put(
        "/resume-chunk/embeddings",
        json={"embeddings": [{"chunkId": chunk_id, "embedding": [0.1] * 8} for chunk_id in stale]},
    )

    assert response.status_code == 422


# --- OS-01: the ranking, which needs no database -----------------------------------


def chunk(text: str, vector: list[float] | None, ordinal: int = 0) -> ResumeChunk:
    return ResumeChunk.model_construct(
        id=PydanticObjectId(),
        section="experience",
        text=text,
        sourceRef="",
        ordinal=ordinal,
        embedding=vector,
    )


@pytest.mark.parametrize(
    ("left", "right", "expected"),
    [
        ([1.0, 0.0], [1.0, 0.0], 1.0),
        ([1.0, 0.0], [0.0, 1.0], 0.0),
        ([1.0, 0.0], [-1.0, 0.0], -1.0),
        # Length does not matter, only direction.
        ([3.0, 4.0], [6.0, 8.0], 1.0),
        ([1.0, 1.0], [1.0, 0.0], 0.7071),
    ],
)
def test_cosine_is_the_plain_cosine(left: list[float], right: list[float], expected: float) -> None:
    """The scale the AI tier's near-miss threshold is measured on. Atlas reported
    `(1 + cosine) / 2` and the server undid it; now nothing rescales anything."""
    assert cosine(left, right) == pytest.approx(expected, abs=1e-4)


def test_a_zero_vector_is_similar_to_nothing() -> None:
    assert cosine([0.0, 0.0], [1.0, 0.0]) == 0.0


def test_results_come_back_best_first_and_stop_at_the_limit() -> None:
    chunks = [
        chunk("unrelated", [0.0, 1.0], 0),
        chunk("exact", [1.0, 0.0], 1),
        chunk("close", [0.9, 0.1], 2),
    ]

    hits = rank(chunks, [1.0, 0.0], limit=2)

    assert [hit.text for hit in hits] == ["exact", "close"]
    assert hits[0].score == pytest.approx(1.0)
    assert hits[0].score > hits[1].score


def test_equal_scores_keep_profile_order() -> None:
    """So the same query answers the same way every time."""
    chunks = [chunk("second", [1.0, 0.0], 5), chunk("first", [2.0, 0.0], 1)]

    assert [hit.text for hit in rank(chunks, [1.0, 0.0], limit=5)] == ["first", "second"]


def test_a_chunk_with_no_vector_is_never_a_hit() -> None:
    chunks = [chunk("edited, not yet embedded", None), chunk("embedded", [1.0, 0.0])]

    assert [hit.text for hit in rank(chunks, [1.0, 0.0], limit=5)] == ["embedded"]


def test_a_vector_from_another_model_is_left_out_not_scored() -> None:
    """A different length means a different embedding model. A cosine between the two
    would be a number that means nothing, and the threshold would act on it."""
    chunks = [chunk("old model", [1.0, 0.0, 0.0]), chunk("this model", [1.0, 0.0])]

    assert [hit.text for hit in rank(chunks, [1.0, 0.0], limit=5)] == ["this model"]


def test_nothing_embedded_answers_with_nothing() -> None:
    assert rank([], [1.0, 0.0], limit=5) == []


# --- OS-01: the search, through the API -----------------------------------------------


async def embed_as(client: AsyncClient, vectors: dict[str, list[float]]) -> None:
    """Give chosen chunks chosen vectors, keyed by the chunk's text."""
    by_text = {row["text"]: row["id"] for row in await chunks(client)}
    response = await client.put(
        "/resume-chunk/embeddings",
        json={
            "embeddings": [
                {"chunkId": by_text[text], "embedding": vector} for text, vector in vectors.items()
            ]
        },
    )
    assert response.status_code == 200, response.text


async def test_search_ranks_this_users_chunks_by_cosine(signed_in: AsyncClient) -> None:
    await signed_in.post("/profile/addSkill", json=SKILLS)
    await embed_as(signed_in, {"LangChain": [0.0, 1.0], "LangGraph": [1.0, 0.0], "RAG": [0.8, 0.6]})

    response = await signed_in.post("/resume-chunk/search", json={"vector": [1.0, 0.0], "limit": 2})

    assert response.status_code == 200, response.text
    hits = response.json()
    assert [hit["text"] for hit in hits] == ["LangGraph", "RAG"]
    assert hits[0]["score"] == pytest.approx(1.0)
    assert hits[1]["score"] == pytest.approx(0.8)


async def test_search_leaves_out_chunks_still_waiting_for_a_vector(
    signed_in: AsyncClient,
) -> None:
    await signed_in.post("/profile/addSkill", json=SKILLS)
    await embed_as(signed_in, {"LangGraph": [1.0, 0.0]})

    hits = (
        await signed_in.post("/resume-chunk/search", json={"vector": [1.0, 0.0], "limit": 10})
    ).json()

    assert [hit["text"] for hit in hits] == ["LangGraph"]


async def test_search_never_returns_another_users_chunk(
    signed_in: AsyncClient, client: AsyncClient
) -> None:
    """The per-user filter. With Atlas it lived in an index definition no test could
    reach; here it is a query, and this is the test."""
    await signed_in.post("/profile/addSkill", json=SKILLS)
    await embed_as(signed_in, {"LangGraph": [1.0, 0.0]})

    other = await client.post(
        "/account/signup",
        json={"name": "Other", "email": "other@example.com", "password": "correct-horse"},
    )
    theirs = {"Authorization": f"Bearer {other.json()['accessToken']}"}

    hits = await client.post(
        "/resume-chunk/search", json={"vector": [1.0, 0.0], "limit": 10}, headers=theirs
    )

    assert hits.status_code == 200, hits.text
    assert hits.json() == []


async def test_search_many_answers_each_vector_in_order(signed_in: AsyncClient) -> None:
    await signed_in.post("/profile/addSkill", json=SKILLS)
    await embed_as(signed_in, {"LangChain": [0.0, 1.0], "LangGraph": [1.0, 0.0]})

    response = await signed_in.post(
        "/resume-chunk/search-many",
        json={"vectors": [[1.0, 0.0], [0.0, 1.0], [1.0, 0.0]], "limit": 1},
    )

    assert response.status_code == 200, response.text
    results = response.json()["results"]
    assert [[hit["text"] for hit in hits] for hits in results] == [
        ["LangGraph"],
        ["LangChain"],
        ["LangGraph"],
    ]


async def test_search_many_on_an_empty_index_answers_empty_lists(
    signed_in: AsyncClient,
) -> None:
    response = await signed_in.post(
        "/resume-chunk/search-many", json={"vectors": [[1.0, 0.0], [0.0, 1.0]]}
    )

    assert response.json() == {"results": [[], []]}


# --- OS-05: a vector belongs to the model that made it --------------------------------


async def embed_with(client: AsyncClient, model: str | None, vector: list[float]) -> None:
    """Embed every chunk with one vector, under `model`."""
    response = await client.put(
        "/resume-chunk/embeddings",
        json={
            "model": model,
            "embeddings": [
                {"chunkId": row["id"], "embedding": vector} for row in await chunks(client)
            ],
        },
    )
    assert response.status_code == 200, response.text


async def pending_for(client: AsyncClient, model: str | None = None) -> list[str]:
    params = {"model": model} if model else {}
    response = await client.get("/resume-chunk/pending", params=params)
    assert response.status_code == 200, response.text
    return [row["text"] for row in response.json()]


async def test_a_chunk_embedded_by_another_model_goes_back_in_the_queue(
    signed_in: AsyncClient,
) -> None:
    """Changing the embedding model must re-embed the profile without anybody clearing
    it by hand. An unchanged chunk keeps its vector through a re-index, so without this
    the old model's vectors would sit there for good."""
    await signed_in.post("/profile/addSkill", json=SKILLS)
    await embed_with(signed_in, "old-model", [1.0, 0.0])

    assert await pending_for(signed_in, "old-model") == []
    assert sorted(await pending_for(signed_in, "new-model")) == ["LangChain", "LangGraph", "RAG"]
    # With no model named the queue means what it always did: chunks with no vector.
    assert await pending_for(signed_in) == []


async def test_a_vector_stored_before_models_were_recorded_counts_as_another_model(
    signed_in: AsyncClient,
) -> None:
    """Every vector already in a database has no model on it. They were made by the
    hosted model this replaced, so they must be embedded again."""
    await signed_in.post("/profile/addSkill", json=SKILLS)
    await embed_with(signed_in, None, [1.0, 0.0])

    assert len(await pending_for(signed_in, "bge-m3")) == 3


async def test_a_search_sees_only_chunks_its_own_model_embedded(
    signed_in: AsyncClient,
) -> None:
    await signed_in.post("/profile/addSkill", json=SKILLS)
    await embed_with(signed_in, "old-model", [1.0, 0.0])

    async def hits(model: str | None) -> list[str]:
        body = {"vectors": [[1.0, 0.0]], "limit": 10}
        if model:
            body["model"] = model
        response = await signed_in.post("/resume-chunk/search-many", json=body)
        assert response.status_code == 200, response.text
        return [hit["text"] for hit in response.json()["results"][0]]

    assert len(await hits("old-model")) == 3
    assert await hits("new-model") == []
    assert len(await hits(None)) == 3


async def test_the_model_survives_a_re_index_with_its_vector(signed_in: AsyncClient) -> None:
    """An unchanged chunk keeps its vector through a re-index, so it must keep the name
    of the model that made it, or the next run would embed the whole profile again."""
    await signed_in.post("/profile/addSkill", json=SKILLS)
    await embed_with(signed_in, "bge-m3", [1.0, 0.0])

    await signed_in.post("/profile/reindex")

    assert await pending_for(signed_in, "bge-m3") == []
