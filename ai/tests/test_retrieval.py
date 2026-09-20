"""P6-04 and P6-05 — filling the index, and searching it.

Neither Voyage nor the server is reachable from a test, so both are stubbed. What is
actually being checked is the wiring the two models make easy to get wrong: which
side of a retrieval goes up as a query and which as a document, that the reranker is
used where it earns its call and kept away from the near-miss threshold, and that
nothing is embedded when nothing changed.
"""

from __future__ import annotations

from collections import namedtuple
from types import SimpleNamespace
from typing import Any

import pytest

from rag import Span, indexing, retrieval

FakeResult = namedtuple("FakeResult", ["index", "relevance_score"])


class FakeEncoder:
    """Stands in for `VoyageEmbeddings`, recording which side each call embedded."""

    calls: list[dict[str, Any]] = []
    vector: list[float] = [1.0, 0.0]

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        FakeEncoder.calls.append({"input_type": "document", "texts": list(texts)})
        return [list(FakeEncoder.vector) for _ in texts]

    async def embed_queries(self, texts: list[str]) -> list[list[float]]:
        FakeEncoder.calls.append({"input_type": "query", "texts": list(texts)})
        return [list(FakeEncoder.vector) for _ in texts]


@pytest.fixture
def encoder(monkeypatch: pytest.MonkeyPatch) -> type[FakeEncoder]:
    FakeEncoder.calls = []
    monkeypatch.setattr(indexing, "VoyageEmbeddings", FakeEncoder)
    monkeypatch.setattr(retrieval, "VoyageEmbeddings", FakeEncoder)
    return FakeEncoder


def hit(text: str, score: float = 0.5) -> dict[str, Any]:
    return {"id": text, "section": "experience", "text": text, "sourceRef": "LTI", "score": score}


# --- P6-04: the index is filled, and only where it is empty ------------------


async def test_nothing_pending_embeds_nothing(
    monkeypatch: pytest.MonkeyPatch, encoder: type[FakeEncoder]
) -> None:
    """`rectify` calls this before every score. If an unchanged profile cost a Voyage
    call per job, it would be the waste P6-04 exists to remove."""
    monkeypatch.setattr(indexing.jobpilot_api, "list_pending_chunks", _returns([]))

    assert await indexing.embed_pending() == 0
    assert encoder.calls == []


async def test_chunks_go_up_as_documents(
    monkeypatch: pytest.MonkeyPatch, encoder: type[FakeEncoder]
) -> None:
    """A profile span is the thing being searched. Sending it as a query embeds it on
    the wrong side of an asymmetric model and costs accuracy silently."""
    monkeypatch.setattr(
        indexing.jobpilot_api, "list_pending_chunks", _returns([{"id": "c1", "text": "LangGraph"}])
    )
    written = _capture(monkeypatch, indexing.jobpilot_api, "store_chunk_embeddings", {"stored": 1})

    assert await indexing.embed_pending() == 1
    assert encoder.calls == [{"input_type": "document", "texts": ["LangGraph"]}]
    assert written[0] == [{"chunkId": "c1", "embedding": [1.0, 0.0]}]


async def test_a_long_profile_is_embedded_in_batches(
    monkeypatch: pytest.MonkeyPatch, encoder: type[FakeEncoder]
) -> None:
    chunks = [{"id": f"c{n}", "text": f"span {n}"} for n in range(5)]
    monkeypatch.setattr(indexing.jobpilot_api, "list_pending_chunks", _returns(chunks))
    written = _capture(monkeypatch, indexing.jobpilot_api, "store_chunk_embeddings", {"stored": 2})

    await indexing.embed_pending(batch_size=2)

    assert [len(batch) for batch in written] == [2, 2, 1]


async def test_index_profile_re_cuts_before_it_embeds(
    monkeypatch: pytest.MonkeyPatch, encoder: type[FakeEncoder]
) -> None:
    """The other order embeds the chunks the profile used to have."""
    order: list[str] = []

    async def reindex() -> dict[str, Any]:
        order.append("reindex")
        return {}

    async def pending(limit: int = 200) -> list[dict[str, Any]]:
        order.append("pending")
        return []

    monkeypatch.setattr(indexing.jobpilot_api, "reindex_profile", reindex)
    monkeypatch.setattr(indexing.jobpilot_api, "list_pending_chunks", pending)
    monkeypatch.setattr(indexing.jobpilot_api, "chunk_stats", _returns({"chunks": 0}))

    await indexing.index_profile()

    assert order == ["reindex", "pending"]


# --- P6-05: wide pass, then the cross-encoder --------------------------------


async def test_the_query_goes_up_as_a_query(
    monkeypatch: pytest.MonkeyPatch, encoder: type[FakeEncoder]
) -> None:
    monkeypatch.setattr(retrieval.jobpilot_api, "search_chunks", _returns([hit("LangGraph")]))

    await retrieval.retrieve("agentic orchestration", top_k=5)

    assert encoder.calls == [{"input_type": "query", "texts": ["agentic orchestration"]}]


async def test_candidates_beyond_the_answer_are_reranked(
    monkeypatch: pytest.MonkeyPatch, encoder: type[FakeEncoder]
) -> None:
    """The bi-encoder scored each chunk without ever seeing the query. The
    cross-encoder reads both together, which is the whole point of the second pass."""
    candidates = [hit(f"span {n}", score=0.9 - n / 100) for n in range(10)]
    monkeypatch.setattr(retrieval.jobpilot_api, "search_chunks", _returns(candidates))
    reranked = _fake_reranker(monkeypatch, [FakeResult(7, 0.88), FakeResult(0, 0.41)])

    spans = await retrieval.retrieve("agentic orchestration", top_k=2)

    assert [span.text for span in spans] == ["span 7", "span 0"]
    assert [span.scored_by for span in spans] == ["rerank", "rerank"]
    assert reranked[0]["top_k"] == 2


async def test_the_reranker_is_skipped_when_it_has_nothing_to_sort(
    monkeypatch: pytest.MonkeyPatch, encoder: type[FakeEncoder]
) -> None:
    """Three candidates for a top five are already the answer, and a second model
    call to confirm their order is one nobody asked for."""
    monkeypatch.setattr(
        retrieval.jobpilot_api, "search_chunks", _returns([hit("a"), hit("b"), hit("c")])
    )
    reranked = _fake_reranker(monkeypatch, [])

    spans = await retrieval.retrieve("agentic orchestration", top_k=5)

    assert [span.scored_by for span in spans] == ["cosine"] * 3
    assert reranked == []


# --- the near-miss path, which must stay on the calibrated scale -------------


async def test_nearest_spans_never_reranks(
    monkeypatch: pytest.MonkeyPatch, encoder: type[FakeEncoder]
) -> None:
    """`NEAR_MISS_THRESHOLD` is a cosine measured against `voyage-4-lite`. A relevance
    score from the cross-encoder sits on a different scale, so handing one to that
    comparison would invalidate the calibration without failing anything."""
    monkeypatch.setattr(retrieval.jobpilot_api, "search_chunks", _returns([hit("LangGraph", 0.52)]))
    reranked = _fake_reranker(monkeypatch, [FakeResult(0, 0.99)])

    spans = await retrieval.nearest_spans(["agentic orchestration"])

    assert spans[0] == Span("LangGraph", "experience", "LangGraph", "LTI", 0.52, "cosine")
    assert reranked == []


async def test_nearest_spans_asks_once_per_label(
    monkeypatch: pytest.MonkeyPatch, encoder: type[FakeEncoder]
) -> None:
    """One embedding call for every label, then one search each: Atlas has no batched
    form of a vector search."""
    searches: list[int] = []

    async def search(vector: list[float], limit: int = 50) -> list[dict[str, Any]]:
        searches.append(limit)
        return [hit("LangGraph")]

    monkeypatch.setattr(retrieval.jobpilot_api, "search_chunks", search)

    await retrieval.nearest_spans(["one", "two", "three"])

    assert encoder.calls == [{"input_type": "query", "texts": ["one", "two", "three"]}]
    assert searches == [1, 1, 1]


async def test_an_empty_index_returns_no_span(
    monkeypatch: pytest.MonkeyPatch, encoder: type[FakeEncoder]
) -> None:
    monkeypatch.setattr(retrieval.jobpilot_api, "search_chunks", _returns([]))

    assert await retrieval.nearest_spans(["agentic orchestration"]) == [None]


async def test_no_labels_asks_nothing(encoder: type[FakeEncoder]) -> None:
    assert await retrieval.nearest_spans([]) == []
    assert encoder.calls == []


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


def _fake_reranker(monkeypatch: pytest.MonkeyPatch, results: list[FakeResult]) -> list[Any]:
    """Records every rerank call, so a test can assert one did not happen."""
    calls: list[dict[str, Any]] = []

    class FakeClient:
        def __init__(self, **kwargs: Any) -> None:
            pass

        async def rerank(self, **kwargs: Any) -> SimpleNamespace:
            calls.append(kwargs)
            return SimpleNamespace(results=results)

    monkeypatch.setattr(retrieval.voyageai, "AsyncClient", FakeClient)
    return calls
