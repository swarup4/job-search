"""The AI tier's HTTP surface — only what the dashboard has to start by hand.

    python -m api.main

Localhost only, like the API server: it acts with whatever token the dashboard
forwards, so nothing off this machine should be able to reach it.
"""

from __future__ import annotations

import os

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import config  # noqa: F401 — imported for its .env load
from api import analysis, capture, discovery, scoring, settings, tailoring


def create_app() -> FastAPI:
    app = FastAPI(title="JobPilot AI", version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        # The unpacked extension, which calls /api/capture right after storing a page.
        allow_origin_regex=r"^chrome-extension://[a-p]{32}$",
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(discovery.router, prefix="/api/runs/discovery")
    app.include_router(settings.router, prefix="/api/settings")
    app.include_router(analysis.router, prefix="/api/runs/analysis")
    app.include_router(tailoring.router, prefix="/api/tailoring")
    app.include_router(scoring.router, prefix="/api/runs/scoring")
    app.include_router(capture.router, prefix="/api/capture")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host=os.environ.get("AI_HOST", "127.0.0.1"),
        port=int(os.environ.get("AI_PORT", "8001")),
    )
