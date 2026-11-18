"""Embeddings for the near-miss check — an open-weights model, served by Ollama.

One OpenAI-compatible endpoint and one model, set by three environment values, the
same way `config/llm.py` reaches the generation model. The default is `bge-m3` on the
Ollama already running for generation, so no profile text and no posting text leaves
the machine to be embedded, and no key is needed.

`bge-m3` embeds every text the same way: a requirement label and a profile span go up
through one call, with no query or document side to get wrong. A model that does treat
the two differently needs that added back here before it is used.
"""

from __future__ import annotations

import asyncio
import math
import os
from collections.abc import Sequence

import httpx

import config  # noqa: F401 — imported for its .env load

EMBED_BASE_URL = os.environ.get("EMBED_BASE_URL", "http://localhost:11434/v1")
EMBED_API_KEY = os.environ.get("EMBED_API_KEY", "")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "bge-m3")
# What the model is expected to return, checked on every reply. A model swapped for
# one of another size would otherwise store vectors the search silently leaves out.
EMBED_DIMS = int(os.environ.get("EMBED_DIMS", "1024"))
EMBED_TIMEOUT = float(os.environ.get("EMBED_TIMEOUT", "120"))
# A local model server drops a request while it loads the model; one more try is the
# difference between a scoring run that finishes and one that loses a job to a cold start.
EMBED_ATTEMPTS = int(os.environ.get("EMBED_ATTEMPTS", "3"))

# The cosine at or above which a profile span is offered as a near miss for a Missing
# requirement. It belongs to one embedding model: a cosine from one model says nothing
# about the scale of another.
#
# PROVISIONAL. Read on 2026-11-18 with `python -m rag.embeddings` on `bge-m3`: the
# 8 related labels scored 0.448–0.604 and the 6 unrelated ones 0.376–0.522, so the two
# groups OVERLAP and no value separates them on that sample. 0.35, the value measured
# for the hosted model this replaced, would flag every one. This sits just above the
# highest unrelated score instead: a missed hint costs nothing, and a wrong one invites
# a claim the user cannot back. It keeps 3 of the 8 real near misses. Whether `bge-m3`
# is good enough at this, and where the line belongs, is settled on the labelled set
# (docs/12, OS-05 and EV-07).
NEAR_MISS_THRESHOLD = float(os.environ.get("NEAR_MISS_THRESHOLD", "0.53"))

type Vector = list[float]


class EmbeddingError(RuntimeError):
    """The embedding model did not answer, or answered with something unusable."""


class Embeddings:
    """Text in, vectors out, in the order given."""

    def __init__(
        self,
        model: str = EMBED_MODEL,
        base_url: str = EMBED_BASE_URL,
        api_key: str = EMBED_API_KEY,
        dimensions: int = EMBED_DIMS,
        attempts: int = EMBED_ATTEMPTS,
        timeout: float = EMBED_TIMEOUT,
    ) -> None:
        self.model = model
        self.dimensions = dimensions
        self._url = f"{base_url.rstrip('/')}/embeddings"
        self._headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._attempts = max(1, attempts)
        self._timeout = timeout

    async def embed(self, texts: Sequence[str]) -> list[Vector]:
        if not texts:
            return []
        body = await self._post({"model": self.model, "input": list(texts)})
        try:
            # Sorted by the index the server reports: the protocol allows any order.
            rows = sorted(body["data"], key=lambda row: row["index"])
            vectors = [[float(value) for value in row["embedding"]] for row in rows]
        except (KeyError, TypeError, ValueError) as error:
            raise EmbeddingError(f"unreadable reply from {self.model}: {error}") from error

        if len(vectors) != len(texts):
            raise EmbeddingError(
                f"{self.model} returned {len(vectors)} vectors for {len(texts)} texts"
            )
        wrong = {len(vector) for vector in vectors} - {self.dimensions}
        if wrong:
            raise EmbeddingError(
                f"{self.model} returned {min(wrong)}-dimension vectors; "
                f"EMBED_DIMS says {self.dimensions}"
            )
        return vectors

    async def _post(self, payload: dict[str, object]) -> dict:
        failure = ""
        for attempt in range(1, self._attempts + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.post(self._url, json=payload, headers=self._headers)
            except httpx.HTTPError as error:
                failure = f"{type(error).__name__}: {error}"
            else:
                if response.status_code < 400:
                    return response.json()
                failure = f"{response.status_code}: {response.text[:200]}"
                # A refused request will be refused again; only a server fault is retried.
                if response.status_code < 500:
                    break
            if attempt < self._attempts:
                await asyncio.sleep(attempt)
        raise EmbeddingError(f"embedding with {self.model} failed — {failure}")


def cosine(a: Vector, b: Vector) -> float:
    # Normalised vectors are common but not promised, so the norms are computed
    # rather than assumed.
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


# A first reading of where the threshold sits for the configured model: requirement
# labels a profile span really covers under other words, and labels it does not.
# Invented for this purpose and small on purpose — the labelled set decides (EV-07).
SPANS = [
    "Built a LangGraph multi-agent pipeline with tool orchestration and memory",
    "Shipped a RAG service over MongoDB with hybrid retrieval",
    "Ran red-team prompt-injection testing before every model release",
    "Deployed FastAPI services to AWS with Docker and GitHub Actions",
    "Led a team of five engineers through a platform migration",
    "Built dashboards in React and TypeScript for the operations team",
]
RELATED = [
    "agentic orchestration",
    "vector databases",
    "retrieval-augmented generation",
    "LLM security testing",
    "CI/CD pipelines",
    "cloud deployment",
    "people management",
    "frontend development",
]
UNRELATED = [
    "COBOL",
    "SAP ABAP",
    "embedded C firmware",
    "iOS development in Swift",
    "Salesforce administration",
    "mainframe batch scheduling",
]


if __name__ == "__main__":

    async def main() -> None:
        """Prints each label's best score in two groups. The threshold goes between
        them: above the highest unrelated score, at or below the lowest related one."""
        model = Embeddings()
        span_vectors = await model.embed(SPANS)
        print(f"model {EMBED_MODEL}, {EMBED_DIMS} dimensions, threshold {NEAR_MISS_THRESHOLD}")

        bounds: dict[str, tuple[float, float]] = {}
        for name, labels in (("related", RELATED), ("unrelated", UNRELATED)):
            scores = []
            for label, vector in zip(labels, await model.embed(labels), strict=True):
                index, score = nearest(vector, span_vectors)
                scores.append(score)
                flag = "NEAR" if score >= NEAR_MISS_THRESHOLD else "  — "
                print(f"{flag}  {score:.3f}  {name:9s} {label:32s} -> {SPANS[index][:44]}")
            bounds[name] = (min(scores), max(scores))

        low_related, high_unrelated = bounds["related"][0], bounds["unrelated"][1]
        print(f"related   {bounds['related'][0]:.3f} to {bounds['related'][1]:.3f}")
        print(f"unrelated {bounds['unrelated'][0]:.3f} to {bounds['unrelated'][1]:.3f}")
        if low_related > high_unrelated:
            print(f"the groups separate: a threshold in ({high_unrelated:.3f}, {low_related:.3f}]")
        else:
            print("the groups overlap: no threshold separates them on this sample")

    asyncio.run(main())
