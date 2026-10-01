"""Public interface of the resume chunk module — the retrieval store.

It holds chunks and searches them. It does not know how to cut a profile up: the
profile module does that and hands the pieces over, which is what keeps the
dependency pointing one way.
"""

from modules.resume_chunk.models import (
    MAX_CHUNK_CHARS,
    MIN_CHUNK_CHARS,
    VECTOR_INDEX,
    ChunkFields,
    ChunkSection,
    IndexStats,
    ResumeChunk,
)
from modules.resume_chunk.router import router
from modules.resume_chunk.service import replace_chunks, search, stats

NAME = "resume-chunk"

__all__ = [
    "MAX_CHUNK_CHARS",
    "MIN_CHUNK_CHARS",
    "NAME",
    "VECTOR_INDEX",
    "ChunkFields",
    "ChunkSection",
    "IndexStats",
    "ResumeChunk",
    "replace_chunks",
    "router",
    "search",
    "stats",
]
