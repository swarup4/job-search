"""P6-04 — filling the index — and the near-miss search over it.

Neither the embedding model nor the server is reachable from a test, so both are
stubbed. What is checked is the wiring: that nothing is embedded when nothing changed,
that a long profile goes up in batches, that a re-index re-cuts before it embeds, and
that every label of a scoring run travels in one embedding call and one search request.
"""

from __future__ import annotations

from typing import Any

import pytest

from rag import Span, indexing, retrieval


class FakeEncoder:
    """Stands in for `Embeddings`, recording what each call was asked to embed."""

    calls: list[list[str]] = []
    vector: list[float] = [1.0, 0.0]
    model = "test-embedder"

    async def embed(self, texts: list[str]) -> list[list[float]]:
        FakeEncoder.calls.append(list(texts))
        return [list(FakeEncoder.vector) for _ in texts]


@pytest.fixture
def encoder(monkeypatch: pytest.MonkeyPatch) -> type[FakeEncoder]:
    FakeEncoder.calls = []
    monkeypatch.setattr(indexing, "Embeddings", FakeEncoder)
    monkeypatch.setattr(retrieval, "Embeddings", FakeEncoder)
    return FakeEncoder


def hit(text: str, score: float = 0.5) -> dict[str, Any]:
    return {"id": text, "section": "experience", "text": text, "sourceRef": "LTI", "score": score}


# --- P6-04: the index is filled, and only where it is empty ------------------


async def test_nothing_pending_embeds_nothing(
    monkeypatch: pytest.MonkeyPatch, encoder: type[FakeEncoder]
) -> None:
    """`rectify` calls this before every score. If an unchanged profile cost a model
    call per job, it would be the waste P6-04 exists to remove."""
    monkeypatch.setattr(indexing.jobpilot_api, "list_pending_chunks", _returns([]))

    assert await indexing.embed_pending() == 0
    assert encoder.calls == []


async def test_pending_chunks_are_embedded_and_stored_against_their_ids(
    monkeypatch: pytest.MonkeyPatch, encoder: type[FakeEncoder]
) -> None:
    monkeypatch.setattr(
        indexing.jobpilot_api, "list_pending_chunks", _returns([{"id": "c1", "text": "LangGraph"}])
    )
    written = _capture(monkeypatch, indexing.jobpilot_api, "store_chunk_embeddings", {"stored": 1})

    assert await indexing.embed_pending() == 1
    assert encoder.calls == [["LangGraph"]]
    assert written[0] == [{"chunkId": "c1", "embedding": [1.0, 0.0]}]


async def test_a_long_profile_is_embedded_in_batches(
    monkeypatch: pytest.MonkeyPatch, encoder: type[FakeEncoder]
) -> None:
    chunks = [{"id": f"c{n}", "text": f"span {n}"} for n in range(5)]
    monkeypatch.setattr(indexing.jobpilot_api, "list_pending_chunks", _returns(chunks))
    written = _capture(monkeypatch, indexing.jobpilot_api, "store_chunk_embeddings", {"stored": 2})

    await indexing.embed_pending(batch_size=2)

    assert [len(batch) for batch in written] == [2, 2, 1]
    assert [len(call) for call in encoder.calls] == [2, 2, 1]


async def test_index_profile_re_cuts_before_it_embeds(
    monkeypatch: pytest.MonkeyPatch, encoder: type[FakeEncoder]
) -> None:
    """The other order embeds the chunks the profile used to have."""
    order: list[str] = []

    async def reindex() -> dict[str, Any]:
        order.append("reindex")
        return {}

    async def pending(limit: int = 200, model: str | None = None) -> list[dict[str, Any]]:
        order.append("pending")
        return []

    monkeypatch.setattr(indexing.jobpilot_api, "reindex_profile", reindex)
    monkeypatch.setattr(indexing.jobpilot_api, "list_pending_chunks", pending)
    monkeypatch.setattr(indexing.jobpilot_api, "chunk_stats", _returns({"chunks": 0}))

    await indexing.index_profile()

    assert order == ["reindex", "pending"]


# --- the near-miss search -------------------------------------------------------


async def test_a_span_carries_the_servers_cosine_unchanged(
    monkeypatch: pytest.MonkeyPatch, encoder: type[FakeEncoder]
) -> None:
    """`NEAR_MISS_THRESHOLD` is compared with this number directly, so nothing between
    the server's cosine and the comparison may rescale it."""
    monkeypatch.setattr(
        retrieval.jobpilot_api, "search_chunks_many", _returns([[hit("LangGraph", 0.52)]])
    )

    spans = await retrieval.nearest_spans(["agentic orchestration"])

    assert spans[0] == Span("LangGraph", "experience", "LangGraph", "LTI", 0.52)


async def test_nearest_spans_sends_every_label_in_one_request(
    monkeypatch: pytest.MonkeyPatch, encoder: type[FakeEncoder]
) -> None:
    """One embedding call for every label and one request for every vector (CE-09).
    It used to be a round trip per label."""
    searches: list[tuple[int, int]] = []

    async def search(
        vectors: list[list[float]], limit: int = 1, model: str | None = None
    ) -> list[list[dict[str, Any]]]:
        searches.append((len(vectors), limit))
        return [[hit("LangGraph")] for _ in vectors]

    monkeypatch.setattr(retrieval.jobpilot_api, "search_chunks_many", search)

    spans = await retrieval.nearest_spans(["one", "two", "three"])

    assert encoder.calls == [["one", "two", "three"]]
    # One request carrying all three vectors, and a span back for each label in order.
    assert searches == [(3, 1)]
    assert len(spans) == 3


async def test_an_empty_index_returns_no_span(
    monkeypatch: pytest.MonkeyPatch, encoder: type[FakeEncoder]
) -> None:
    monkeypatch.setattr(retrieval.jobpilot_api, "search_chunks_many", _returns([[]]))

    assert await retrieval.nearest_spans(["agentic orchestration"]) == [None]


async def test_no_labels_asks_nothing(encoder: type[FakeEncoder]) -> None:
    assert await retrieval.nearest_spans([]) == []
    assert encoder.calls == []


# --- OS-05: every vector is tied to the model that made it ----------------------


async def test_the_queue_the_vectors_and_the_search_all_name_the_model(
    monkeypatch: pytest.MonkeyPatch, encoder: type[FakeEncoder]
) -> None:
    """A cosine between two models' vectors means nothing. The queue is asked for
    chunks this model has not embedded, the vectors are stored under its name, and the
    search looks only at chunks it embedded — so changing EMBED_MODEL re-embeds the
    profile on the next run and never mixes the two."""
    seen: dict[str, Any] = {}

    async def pending(limit: int = 200, model: str | None = None) -> list[dict[str, Any]]:
        seen["queue"] = model
        return [{"id": "c1", "text": "LangGraph"}]

    async def store(embeddings: list[dict[str, Any]], model: str | None = None) -> dict[str, Any]:
        seen["stored"] = model
        return {"stored": len(embeddings)}

    async def search(
        vectors: list[list[float]], limit: int = 1, model: str | None = None
    ) -> list[list[dict[str, Any]]]:
        seen["searched"] = model
        return [[] for _ in vectors]

    monkeypatch.setattr(indexing.jobpilot_api, "list_pending_chunks", pending)
    monkeypatch.setattr(indexing.jobpilot_api, "store_chunk_embeddings", store)
    monkeypatch.setattr(retrieval.jobpilot_api, "search_chunks_many", search)

    await indexing.embed_pending()
    await retrieval.nearest_spans(["agentic orchestration"])

    assert seen == {
        "queue": "test-embedder",
        "stored": "test-embedder",
        "searched": "test-embedder",
    }


def test_two_stage_retrieval_is_gone_with_the_chat() -> None:
    """OS-03: `retrieve` and `rerank` answered questions in a conversation and had no
    other caller. They come back with the chat, not before."""
    assert not hasattr(retrieval, "retrieve") and not hasattr(retrieval, "rerank")


# --- stubs -------------------------------------------------------------------


def _returns(value: Any):
    async def stub(*args: Any, **kwargs: Any) -> Any:
        return value

    return stub


def _capture(monkeypatch: pytest.MonkeyPatch, target: Any, name: str, value: Any) -> list[Any]:
    """Replace `target.name` with a stub that records its first argument."""
    seen: list[Any] = []

    async def stub(first: Any, *args: Any, **kwargs: Any) -> Any:
        seen.append(first)
        return value

    monkeypatch.setattr(target, name, stub)
    return seen
