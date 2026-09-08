import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.database import connect, disconnect
from errors import DomainError, handle_domain_error
from modules import application, event, job, match, profile, resume, user

MODULES = (job, match, resume, application, event, profile, user)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    await connect()
    yield
    await disconnect()


def create_app() -> FastAPI:
    app = FastAPI(title="JobPilot API", version="1.0.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        # NFR-4: the local dashboard and the unpacked extension. Nothing else.
        allow_origins=[os.environ.get("WEB_ORIGIN", "http://localhost:3000")],
        allow_origin_regex=r"^chrome-extension://[a-p]{32}$",
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Every service error reaches HTTP here — see errors.py.
    app.add_exception_handler(DomainError, handle_domain_error)

    for module in MODULES:
        app.include_router(module.router, prefix=f"/api/{module.NAME}")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        # NFR-4 — bind loopback, never 0.0.0.0.
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8000")),
        reload=True,
    )
