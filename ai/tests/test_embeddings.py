"""The near-miss arithmetic, and the embedding call it rests on. (OS-02)"""

from __future__ import annotations

from typing import Any, Self

import httpx
import pytest

from rag import embeddings
from rag.embeddings import EmbeddingError, Embeddings, cosine, nearest


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


# --- the call itself, against a stubbed model server --------------------------


class FakeServer:
    """Stands in for the model server's `/embeddings`, answering from a queue and
    recording every request."""

    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []
        self.replies: list[Any] = []

    def reply(self, *vectors: list[float], status: int = 200) -> None:
        data = [{"index": index, "embedding": vector} for index, vector in enumerate(vectors)]
        self.replies.append(httpx.Response(status, json={"data": data}))

    def client(self, **kwargs: Any) -> FakeClient:
        return FakeClient(self)


class FakeClient:
    def __init__(self, server: FakeServer) -> None:
        self.server = server

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    async def post(self, url: str, *, json: dict[str, Any], headers: dict[str, str]) -> Any:
        self.server.requests.append({"url": url, "json": json, "headers": headers})
        reply = self.server.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


@pytest.fixture
def server(monkeypatch: pytest.MonkeyPatch) -> FakeServer:
    fake = FakeServer()
    monkeypatch.setattr(embeddings.httpx, "AsyncClient", fake.client)

    async def no_wait(seconds: float) -> None:
        return None

    monkeypatch.setattr(embeddings.asyncio, "sleep", no_wait)
    return fake


def model(**overrides: Any) -> Embeddings:
    return Embeddings(**{"dimensions": 2, **overrides})


async def test_texts_go_up_in_one_request_to_the_configured_model(server: FakeServer) -> None:
    server.reply([1.0, 0.0], [0.0, 1.0])

    vectors = await model(model="bge-m3", base_url="http://localhost:11434/v1/").embed(["a", "b"])

    assert vectors == [[1.0, 0.0], [0.0, 1.0]]
    [request] = server.requests
    assert request["url"] == "http://localhost:11434/v1/embeddings"
    assert request["json"] == {"model": "bge-m3", "input": ["a", "b"]}


async def test_a_local_model_is_sent_no_key(server: FakeServer) -> None:
    """There is none to send, and an empty bearer header is noise a server may refuse."""
    server.reply([1.0, 0.0])

    await model(api_key="").embed(["a"])

    assert server.requests[0]["headers"] == {}


async def test_vectors_come_back_in_the_order_the_texts_went_up(server: FakeServer) -> None:
    """The protocol reports an index with each vector and promises no order. A vector
    stored on the wrong chunk is a wrong hint nobody would trace back to this."""
    server.replies.append(
        httpx.Response(
            200,
            json={
                "data": [
                    {"index": 1, "embedding": [0.0, 1.0]},
                    {"index": 0, "embedding": [1.0, 0.0]},
                ]
            },
        )
    )

    assert await model().embed(["first", "second"]) == [[1.0, 0.0], [0.0, 1.0]]


async def test_no_texts_asks_nothing(server: FakeServer) -> None:
    assert await model().embed([]) == []
    assert server.requests == []


async def test_a_model_of_another_size_is_refused(server: FakeServer) -> None:
    """Vectors of the wrong length would be stored and then silently left out of every
    search. Refusing them here names the cause."""
    server.reply([1.0, 0.0, 0.0])

    with pytest.raises(EmbeddingError, match="3-dimension"):
        await model(dimensions=2).embed(["a"])


async def test_fewer_vectors_than_texts_is_refused(server: FakeServer) -> None:
    server.reply([1.0, 0.0])

    with pytest.raises(EmbeddingError, match="1 vectors for 2 texts"):
        await model().embed(["a", "b"])


async def test_a_server_fault_is_tried_again(server: FakeServer) -> None:
    """A local model server drops a request while it loads the model."""
    server.reply(status=503)
    server.replies.append(httpx.ConnectError("refused"))
    server.reply([1.0, 0.0])

    assert await model(attempts=3).embed(["a"]) == [[1.0, 0.0]]
    assert len(server.requests) == 3


async def test_a_refused_request_is_not_tried_again(server: FakeServer) -> None:
    """A 404 for a model that was never pulled will be a 404 the second time too."""
    server.replies.append(httpx.Response(404, text='model "bge-m3" not found'))

    with pytest.raises(EmbeddingError, match="404"):
        await model(attempts=3).embed(["a"])
    assert len(server.requests) == 1


async def test_a_model_that_never_answers_ends_in_an_error_naming_it(server: FakeServer) -> None:
    for _ in range(2):
        server.replies.append(httpx.ConnectError("refused"))

    with pytest.raises(EmbeddingError, match="bge-m3"):
        await model(model="bge-m3", attempts=2).embed(["a"])


def test_the_default_endpoint_is_this_machine() -> None:
    """Embedding is the one step that sends profile text to a model besides generation.
    Its default must not be somebody else's server."""
    host = httpx.URL(embeddings.EMBED_BASE_URL).host

    assert host in {"localhost", "127.0.0.1"}
