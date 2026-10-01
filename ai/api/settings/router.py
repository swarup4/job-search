"""What this tier is actually configured with, for the Settings screen to show.

Read-only and from the environment. Search targets are not here: those are saved
per account on the API server and read at the start of each run.
"""

from __future__ import annotations

from fastapi import APIRouter

from api.deps import Caller
from api.settings.models import ModelSettings, ScrapeSettings, TierSettings
from config.llm import LLM_HOST, LLM_MODEL
from rag.embeddings import VOYAGE_EMBED_MODEL
from rag.retrieval import VOYAGE_RERANK_MODEL
from sources.http import MAX_PER_HOST, USER_AGENT

router = APIRouter(tags=["settings"])


@router.get("", response_model=TierSettings)
async def read_settings(_: Caller) -> TierSettings:
    return TierSettings(
        scrape=ScrapeSettings(maxPerHost=MAX_PER_HOST, userAgent=USER_AGENT),
        models=ModelSettings(
            generation=LLM_MODEL,
            generationHost=LLM_HOST,
            embeddings=VOYAGE_EMBED_MODEL,
            rerank=VOYAGE_RERANK_MODEL,
        ),
    )
