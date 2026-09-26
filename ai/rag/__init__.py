"""Public interface of the rag package — the retrieval layer over your own profile.

Three files, in the order a chunk passes through them: `embeddings` turns text into
vectors, `indexing` fills the index the server stores, `retrieval` searches it.
Nothing here reaches a database. `$vectorSearch` runs on `server`, which is the tier
that holds a URI; this one holds the models and their keys.
"""

from rag.embeddings import (
    NEAR_MISS_THRESHOLD,
    VOYAGE_EMBED_DIMS,
    VOYAGE_EMBED_MODEL,
    Vector,
    VoyageEmbeddings,
    cosine,
    nearest,
)
from rag.indexing import EMBED_BATCH, embed_pending, index_profile
from rag.retrieval import (
    RETRIEVE_CANDIDATES,
    RETRIEVE_TOP_K,
    VOYAGE_RERANK_MODEL,
    Span,
    nearest_spans,
    rerank,
    retrieve,
)

__all__ = [
    "EMBED_BATCH",
    "NEAR_MISS_THRESHOLD",
    "RETRIEVE_CANDIDATES",
    "RETRIEVE_TOP_K",
    "VOYAGE_EMBED_DIMS",
    "VOYAGE_EMBED_MODEL",
    "VOYAGE_RERANK_MODEL",
    "Span",
    "Vector",
    "VoyageEmbeddings",
    "cosine",
    "embed_pending",
    "index_profile",
    "nearest",
    "nearest_spans",
    "rerank",
    "retrieve",
]
