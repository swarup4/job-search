"""Giving the profile's chunks their vectors. (P6-04)

The server cuts My Details into chunks and stores them with no vector; this is the
half that needs a model, so it lives here with the embedding model. A chunk with no
vector is invisible to search, which is what makes the split safe: between a profile
edit and the next run here, retrieval returns nothing rather than returning what the
user just replaced.
"""

from __future__ import annotations

import asyncio
import sys
from typing import Any

from mcp_servers import jobpilot_api
from rag.embeddings import Embeddings

# A local model embeds a batch in one pass and holds all of it in memory while it
# does. An ordinary profile is forty chunks, so this is two requests, and a long one
# never sends a batch the model server has to refuse.
EMBED_BATCH = 32


async def embed_pending(batch_size: int = EMBED_BATCH) -> int:
    """Embed every chunk still waiting for a vector. Returns how many were written.

    Cheap when there is nothing to do — one GET — which is what lets `rectify` call
    it before scoring rather than trusting that somebody ran an indexing job.
    """
    model = Embeddings()
    # Naming the model puts chunks another model embedded back in the queue, so a
    # change of EMBED_MODEL re-embeds the profile on the next run and never mixes two
    # models' vectors in one search.
    pending = await jobpilot_api.list_pending_chunks(model=model.model)
    if not pending:
        return 0

    stored = 0
    for start in range(0, len(pending), batch_size):
        batch = pending[start : start + batch_size]
        vectors = await model.embed([chunk["text"] for chunk in batch])
        result = await jobpilot_api.store_chunk_embeddings(
            [
                {"chunkId": chunk["id"], "embedding": vector}
                for chunk, vector in zip(batch, vectors, strict=True)
            ],
            model=model.model,
        )
        stored += result["stored"]
    return stored


async def index_profile() -> dict[str, Any]:
    """Re-cut the profile and embed whatever that produced. The full pass, for a
    first run or after an edit; `embed_pending` alone is the incremental one."""
    await jobpilot_api.reindex_profile()
    await embed_pending()
    return await jobpilot_api.chunk_stats()


if __name__ == "__main__":

    async def main() -> None:
        token = sys.argv[1] if len(sys.argv) > 1 else ""
        if not token:
            print("usage: python rag/indexing.py <jwt>")
            return
        jobpilot_api.set_token(token)
        stats = await index_profile()
        print(
            f"{stats['chunks']} chunks, {stats['embedded']} embedded, "
            f"{stats['pending']} pending, last indexed {stats['lastIndexedAt']}"
        )

    asyncio.run(main())
