"""Retrieval over your own profile: `$vectorSearch` → rerank → the few that matter. (P6-05)

Two models, doing two different jobs. `voyage-4-lite` is cheap enough to embed every
chunk, so it does the wide pass — fifty candidates out of the whole profile. It is a
bi-encoder: it turned each chunk into a vector without ever seeing the query, which
is what makes the index possible and what limits how well it can rank. The reranker
is a cross-encoder — it reads the query and the chunk together — so it sorts those
fifty far better than a cosine can, and is far too expensive to run over everything.

Search runs on the server: this tier has no database URI, and `$vectorSearch` needs
one. Everything a model touches happens here.
"""

from __future__ import annotations

import asyncio
import os
import sys
from dataclasses import dataclass

import voyageai

import config  # noqa: F401 — imported for its .env load
from mcp_servers import jobpilot_api
from rag.embeddings import NEAR_MISS_THRESHOLD, VoyageEmbeddings

VOYAGE_RERANK_MODEL = os.environ.get("VOYAGE_RERANK_MODEL", "rerank-2.5-lite")

# Wide enough that the right chunk is in there for the reranker to find, which is the
# only job this number has. A profile is a few dozen chunks, so this is usually all
# of them.
RETRIEVE_CANDIDATES = 50
RETRIEVE_TOP_K = 5


@dataclass(frozen=True, slots=True)
class Span:
    """One retrieved chunk of the profile.

    `scored_by` is not decoration. A cosine and a reranker's relevance are different
    scales — `NEAR_MISS_THRESHOLD` is calibrated against the first and means nothing
    against the second — so a span says which one it carries.
    """

    id: str
    section: str
    text: str
    source_ref: str
    score: float
    scored_by: str


async def retrieve(
    query: str,
    top_k: int = RETRIEVE_TOP_K,
    candidates: int = RETRIEVE_CANDIDATES,
) -> list[Span]:
    """The spans of the profile that answer `query`, best first."""
    hits = await _search(query, candidates)
    if len(hits) <= top_k:
        # Nothing to sort out: reranking a list that is already the answer buys a
        # better order at the price of a second model call.
        return hits[:top_k]
    return await rerank(query, hits, top_k)


async def rerank(query: str, spans: list[Span], top_k: int = RETRIEVE_TOP_K) -> list[Span]:
    """Re-sort candidates with a cross-encoder, which reads query and chunk together.

    ~50 chunks of a few dozen tokens is ~2k tokens a query, so this costs well under
    a hundredth of a cent — next to the ~$0.001 a job the LLM costs, it is noise.
    """
    client = voyageai.AsyncClient(api_key=os.getenv("VOYAGE_API_KEY"), max_retries=2, timeout=30.0)
    ranking = await client.rerank(
        query=query,
        documents=[span.text for span in spans],
        model=VOYAGE_RERANK_MODEL,
        top_k=top_k,
    )
    return [
        Span(
            id=spans[result.index].id,
            section=spans[result.index].section,
            text=spans[result.index].text,
            source_ref=spans[result.index].source_ref,
            score=result.relevance_score,
            scored_by="rerank",
        )
        for result in ranking.results
    ]


async def nearest_spans(labels: list[str]) -> list[Span | None]:
    """The closest profile span to each label, or None where the index has nothing.

    Deliberately not reranked. This feeds the near-miss check, whose threshold is a
    cosine measured in `rag/embeddings.py`; a relevance score from the cross-encoder
    would sit on a different scale and quietly invalidate that calibration.
    """
    if not labels:
        return []

    # One embedding call for every label, then one search each — the search is what
    # Atlas has to do per query vector, and there is no batched form of it.
    vectors = await VoyageEmbeddings().embed_queries(labels)
    spans: list[Span | None] = []
    for vector in vectors:
        hits = await jobpilot_api.search_chunks(vector, limit=1)
        spans.append(_span(hits[0]) if hits else None)
    return spans


async def _search(query: str, limit: int) -> list[Span]:
    """The wide pass. The query goes up as `query`, the chunks went up as `document`:
    asking which span answers a question is a retrieval, not a symmetry."""
    vectors = await VoyageEmbeddings().embed_queries([query])
    return [_span(hit) for hit in await jobpilot_api.search_chunks(vectors[0], limit)]


def _span(hit: dict) -> Span:
    # `score` arrives as a true cosine: the server undoes Atlas's `(1 + cosine) / 2`
    # before it answers.
    return Span(
        id=hit["id"],
        section=hit["section"],
        text=hit["text"],
        source_ref=hit.get("sourceRef", ""),
        score=hit["score"],
        scored_by="cosine",
    )


if __name__ == "__main__":

    async def main() -> None:
        """`python rag/retrieval.py <jwt> "agentic orchestration"` — the two passes
        side by side, so a bad rerank is visible rather than inferred."""
        token = sys.argv[1] if len(sys.argv) > 1 else ""
        query = sys.argv[2] if len(sys.argv) > 2 else "agentic orchestration"
        if not token:
            print('usage: python rag/retrieval.py <jwt> "<query>"')
            return

        jobpilot_api.set_token(token)
        wide = await _search(query, RETRIEVE_CANDIDATES)
        print(f"{len(wide)} candidates for {query!r}, near-miss threshold {NEAR_MISS_THRESHOLD}")
        for span in wide[:RETRIEVE_TOP_K]:
            print(f"  cosine {span.score:.3f}  {span.section:14s} {span.text[:60]}")

        print("reranked:")
        for span in await retrieve(query):
            print(f"  {span.scored_by} {span.score:.3f}  {span.section:14s} {span.text[:60]}")

    asyncio.run(main())
