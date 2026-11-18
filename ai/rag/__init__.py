"""Public interface of the rag package — the search over your own profile.

Three files, in the order a chunk passes through them: `embeddings` turns text into
vectors, `indexing` fills the index the server stores, `retrieval` searches it.
Nothing here reaches a database. The search runs on `server`, which holds the chunks;
this tier holds the embedding model.
"""

from rag.embeddings import (
    EMBED_DIMS,
    EMBED_MODEL,
    NEAR_MISS_THRESHOLD,
    EmbeddingError,
    Embeddings,
    Vector,
    cosine,
    nearest,
)
from rag.indexing import EMBED_BATCH, embed_pending, index_profile
from rag.retrieval import Span, nearest_spans

__all__ = [
    "EMBED_BATCH",
    "EMBED_DIMS",
    "EMBED_MODEL",
    "NEAR_MISS_THRESHOLD",
    "EmbeddingError",
    "Embeddings",
    "Span",
    "Vector",
    "cosine",
    "embed_pending",
    "index_profile",
    "nearest",
    "nearest_spans",
]
