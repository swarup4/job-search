"""The search over your own profile that scoring uses: the nearest chunk to each
Missing requirement.

The search itself runs on the server, which holds the chunks and their vectors: an
exact cosine over one user's few dozen chunks. This tier holds the embedding model, so
it turns each label into a vector here and sends the vectors across.

Two-stage retrieval and its reranker lived here until docs/12 parked the chat: they
answered a question in a conversation, and nothing else called them.
"""

from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass

import config  # noqa: F401 — imported for its .env load
from mcp_servers import jobpilot_api
from rag.embeddings import NEAR_MISS_THRESHOLD, Embeddings


@dataclass(frozen=True, slots=True)
class Span:
    """One chunk of the profile, and its cosine against the label it was found for.
    `NEAR_MISS_THRESHOLD` is measured on this scale and no other."""

    id: str
    section: str
    text: str
    source_ref: str
    score: float


async def nearest_spans(labels: list[str]) -> list[Span | None]:
    """The closest profile span to each label, or None where the index has nothing."""
    if not labels:
        return []

    # One embedding call for every label, then one request carrying every vector.
    # The search is told which model the vectors came from, and looks only at chunks
    # the same model embedded.
    model = Embeddings()
    vectors = await model.embed(labels)
    results = await jobpilot_api.search_chunks_many(vectors, limit=1, model=model.model)
    return [_span(hits[0]) if hits else None for hits in results]


def _span(hit: dict) -> Span:
    return Span(
        id=hit["id"],
        section=hit["section"],
        text=hit["text"],
        source_ref=hit.get("sourceRef", ""),
        score=hit["score"],
    )


if __name__ == "__main__":

    async def main() -> None:
        """`python -m rag.retrieval <jwt> "agentic orchestration"` — the nearest span
        of your profile to a label, and which side of the threshold it falls."""
        token = sys.argv[1] if len(sys.argv) > 1 else ""
        labels = sys.argv[2:] or ["agentic orchestration"]
        if not token:
            print('usage: python -m rag.retrieval <jwt> "<label>" ...')
            return

        jobpilot_api.set_token(token)
        for label, span in zip(labels, await nearest_spans(labels), strict=True):
            if span is None:
                print(f"  —   {label}: nothing indexed")
                continue
            flag = "NEAR" if span.score >= NEAR_MISS_THRESHOLD else "  — "
            print(f"{flag}  {span.score:.3f}  {label:28s} -> {span.text[:60]}")

    asyncio.run(main())
