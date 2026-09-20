"""Giving the profile's chunks their vectors. (P6-04)

The server cuts My Details into chunks and stores them with no vector; this is the
half that costs money and a network call, so it lives here with the embedding model
and its key. A chunk with no vector is invisible to `$vectorSearch`, which is what
makes the split safe: between a profile edit and the next run here, retrieval
returns nothing rather than returning what the user just replaced.
"""

from __future__ import annotations

import asyncio
import sys
from typing import Any

from mcp_servers import jobpilot_api
from rag.embeddings import VoyageEmbeddings

# Voyage takes a whole profile in one request. The batch exists for the pathological
# profile, not the ordinary one — forty chunks go up as a single call.
EMBED_BATCH = 128


async def embed_pending(batch_size: int = EMBED_BATCH) -> int:
    """Embed every chunk still waiting for a vector. Returns how many were written.

    Cheap when there is nothing to do — one GET — which is what lets `rectify` call
    it before scoring rather than trusting that somebody ran an indexing job.
    """
    pending = await jobpilot_api.list_pending_chunks()
    if not pending:
        return 0

    voyage = VoyageEmbeddings()
    stored = 0
    for start in range(0, len(pending), batch_size):
        batch = pending[start : start + batch_size]
        # Chunks go up as `document`: a profile span is the thing being searched, and
        # Voyage embeds the two sides of a retrieval differently.
        vectors = await voyage.embed_documents([chunk["text"] for chunk in batch])
        result = await jobpilot_api.store_chunk_embeddings(
            [
                {"chunkId": chunk["id"], "embedding": vector}
                for chunk, vector in zip(batch, vectors, strict=True)
            ]
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
