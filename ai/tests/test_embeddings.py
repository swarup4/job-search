"""The near-miss arithmetic, and the Voyage call it rests on."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from rag import embeddings
from rag.embeddings import VoyageEmbeddings, cosine, nearest


def test_identical_directions_score_one() -> None:
    assert cosine([1.0, 0.0], [2.0, 0.0]) == 1.0


def test_orthogonal_directions_score_zero() -> None:
    assert cosine([1.0, 0.0], [0.0, 1.0]) == 0.0


def test_a_zero_vector_scores_zero_rather_than_dividing_by_it() -> None:
    assert cosine([0.0, 0.0], [1.0, 0.0]) == 0.0


def test_nearest_picks_the_closest_candidate() -> None:
    index, score = nearest([1.0, 0.0], [[0.0, 1.0], [0.9, 0.1], [0.5, 0.5]])
    assert index == 1
    assert score > 0.9


def test_nearest_on_nothing_is_not_a_match() -> None:
    assert nearest([1.0, 0.0], []) == (-1, 0.0)


# --- the Voyage call itself, against a stubbed SDK client --------------------


class FakeVoyage:
    """Stands in for `voyageai.AsyncClient`, recording how it was constructed and
    called so a test can assert on both."""

    constructed: list[dict[str, Any]] = []
    calls: list[dict[str, Any]] = []
    vectors: list[list[float]] = []

    def __init__(self, **kwargs: Any) -> None:
        FakeVoyage.constructed.append(kwargs)

    async def embed(self, texts: list[str], **kwargs: Any) -> SimpleNamespace:
        FakeVoyage.calls.append({"texts": texts, **kwargs})
        return SimpleNamespace(embeddings=FakeVoyage.vectors)


@pytest.fixture
def voyage(monkeypatch: pytest.MonkeyPatch) -> type[FakeVoyage]:
    FakeVoyage.constructed, FakeVoyage.calls, FakeVoyage.vectors = [], [], []
    monkeypatch.setattr(embeddings.voyageai, "AsyncClient", FakeVoyage)
    return FakeVoyage


async def test_the_two_sides_go_up_differently(voyage: type[FakeVoyage]) -> None:
    """Voyage embeds a query and a document differently, so sending them the same way
    would quietly cost accuracy the threshold then gets blamed for."""
    voyage.vectors = [[1.0, 0.0], [0.0, 1.0]]
    encoder = VoyageEmbeddings()

    assert await encoder.embed_documents(["a", "b"]) == [[1.0, 0.0], [0.0, 1.0]]
    assert await encoder.embed_queries(["a", "b"]) == [[1.0, 0.0], [0.0, 1.0]]

    assert [call["input_type"] for call in voyage.calls] == ["document", "query"]
    assert voyage.calls[0]["texts"] == ["a", "b"]


async def test_the_dimension_is_asked_for_not_assumed(voyage: type[FakeVoyage]) -> None:
    """It has to equal the Atlas index's numDimensions, and a model default that moved
    would leave the two disagreeing with no error at all."""
    voyage.vectors = [[1.0, 0.0]]

    await VoyageEmbeddings().embed_queries(["anything"])

    assert voyage.calls[0]["output_dimension"] == embeddings.VOYAGE_EMBED_DIMS
    assert voyage.calls[0]["model"] == embeddings.VOYAGE_EMBED_MODEL


async def test_retries_are_asked_for(voyage: type[FakeVoyage]) -> None:
    """The SDK retries nothing by default, and the free tier rate-limits at 3 calls a
    minute, so a burst mid-scoring would otherwise lose the run."""
    VoyageEmbeddings()

    assert voyage.constructed[0]["max_retries"] >= 1
