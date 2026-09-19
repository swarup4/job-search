"""Embeddings for the near-miss check — Voyage AI, hosted.

Labels go up as `query` and profile spans as `document`: Voyage embeds the two
asymmetrically, and asking whether a requirement appears in a span is a retrieval
rather than a symmetry.

This is the one place profile text leaves the machine, which is what narrows NFR-3
from "nothing leaves" to "all generation is local".
"""

from __future__ import annotations

import math
import os
from collections.abc import Sequence

import voyageai

import config  # noqa: F401 — imported for its .env load

VOYAGE_EMBED_MODEL = os.environ.get("VOYAGE_EMBED_MODEL", "voyage-4-lite")
# Asked for explicitly: this has to equal `numDimensions` on the Atlas index in
# `server/config/database.py`, and a model default that moved would leave the two
# disagreeing with no error, just no matches.
VOYAGE_EMBED_DIMS = int(os.environ.get("VOYAGE_EMBED_DIMS", "1024"))

# Calibrated 2026-09-19 on voyage-4-lite: 14 labels over 6 profile spans, related
# scoring 0.368–0.544 and unrelated 0.219–0.324. Sits above the midpoint of that gap
# because a missed hint costs nothing and a wrong one invites a claim the user cannot
# back. A cosine from one model says nothing about the scale of another, so re-run
# `python rag/embeddings.py` whenever the model changes.
NEAR_MISS_THRESHOLD = float(os.environ.get("NEAR_MISS_THRESHOLD", "0.35"))

type Vector = list[float]


class VoyageEmbeddings:
    """voyage-4-lite embeddings, one call per side of the comparison."""

    def __init__(
        self,
        model: str = VOYAGE_EMBED_MODEL,
        output_dimension: int = VOYAGE_EMBED_DIMS,
        api_key: str | None = None,
        max_retries: int = 2,
        timeout: float = 30.0,
    ) -> None:
        self.model = model
        self.output_dimension = output_dimension
        self._client = voyageai.AsyncClient(
            api_key=api_key or os.getenv("VOYAGE_API_KEY"),
            max_retries=max_retries,
            timeout=timeout,
        )

    async def embed_documents(self, texts: Sequence[str]) -> list[Vector]:
        return await self._embed(texts, "document")

    async def embed_queries(self, texts: Sequence[str]) -> list[Vector]:
        return await self._embed(texts, "query")

    async def _embed(self, texts: Sequence[str], input_type: str) -> list[Vector]:
        result = await self._client.embed(
            list(texts),
            model=self.model,
            input_type=input_type,
            output_dimension=self.output_dimension,
        )
        return result.embeddings


def cosine(a: Vector, b: Vector) -> float:
    # Voyage returns normalised vectors but does not promise to, so the norms are
    # computed rather than assumed.
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


def nearest(probe: Vector, candidates: Sequence[Vector]) -> tuple[int, float]:
    """Index and score of the candidate closest to `probe`; `(-1, 0.0)` when empty."""
    best_index, best_score = -1, 0.0
    for index, candidate in enumerate(candidates):
        score = cosine(probe, candidate)
        if score > best_score:
            best_index, best_score = index, score
    return best_index, best_score


if __name__ == "__main__":
    import asyncio

    async def main() -> None:
        """Where `NEAR_MISS_THRESHOLD` should sit: put the line between the two groups
        this prints."""
        labels = ["agentic orchestration", "vector databases", "Kubernetes", "COBOL"]
        spans = [
            "Built a LangGraph multi-agent pipeline with tool orchestration and memory",
            "Shipped a RAG service over MongoDB Atlas with hybrid retrieval",
            "Ran red-team prompt-injection testing before every model release",
        ]
        voyage = VoyageEmbeddings()
        label_vectors = await voyage.embed_queries(labels)
        span_vectors = await voyage.embed_documents(spans)

        print(
            f"model {VOYAGE_EMBED_MODEL}, dim {VOYAGE_EMBED_DIMS}, threshold {NEAR_MISS_THRESHOLD}"
        )
        for label, vector in zip(labels, label_vectors, strict=True):
            index, score = nearest(vector, span_vectors)
            flag = "NEAR" if score >= NEAR_MISS_THRESHOLD else "  — "
            print(f"{flag}  {score:.3f}  {label:24s} -> {spans[index][:58]}")

    asyncio.run(main())
