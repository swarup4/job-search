"""The AI tier's HTTP surface — only what the dashboard has to start by hand.

Localhost only, like the API server: it acts with whatever token the dashboard
forwards, so nothing off this machine should be able to reach it.
"""

from __future__ import annotations

import logging
import os

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import config  # noqa: F401 — imported for its .env load
from api import analysis, capture, discovery, scoring, settings, tailoring
from config.error_log import ErrorLogHandler
from config.errors import DomainError, handle_domain_error

MODULES = (discovery, analysis, scoring, tailoring, capture, settings)


def create_app() -> FastAPI:
    handler = ErrorLogHandler("ai")
    # Uvicorn reports an exception a route lets escape on its own logger, which does
    # not propagate to the root.
    for logger in (logging.getLogger(), logging.getLogger("uvicorn.error")):
        if not any(isinstance(existing, ErrorLogHandler) for existing in logger.handlers):
            logger.addHandler(handler)

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

    # Every service error reaches HTTP here — see config/errors.py.
    app.add_exception_handler(DomainError, handle_domain_error)

    for module in MODULES:
        app.include_router(module.router, prefix=f"/api/{module.PREFIX}")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        # NFR-4 — bind loopback, never 0.0.0.0.
        host=os.environ.get("AI_HOST", "127.0.0.1"),
        port=int(os.environ.get("AI_PORT", "8001")),
    )
