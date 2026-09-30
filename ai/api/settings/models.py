from __future__ import annotations

from pydantic import BaseModel


class ScrapeSettings(BaseModel):
    maxPerHost: int
    userAgent: str


class ModelSettings(BaseModel):
    generation: str
    generationHost: str
    embeddings: str
    rerank: str


class TierSettings(BaseModel):
    scrape: ScrapeSettings
    models: ModelSettings
