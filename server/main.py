from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from config.database import connect, disconnect
from config.settings import get_settings
from modules import application, event, job, match, profile, resume

MODULES = (job, match, resume, application, event, profile)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    await connect()
    yield
    await disconnect()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="JobPilot API", version="0.1.0", lifespan=lifespan)

    from fastapi.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        # NFR-4: the local dashboard and the unpacked extension. Nothing else.
        allow_origins=settings.cors_origins,
        allow_origin_regex=r"^chrome-extension://[a-p]{32}$",
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    for module in MODULES:
        app.include_router(module.router, prefix=f"/api/{module.NAME}")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    # NFR-4 — bind loopback, never 0.0.0.0.
    uvicorn.run("main:app", host=settings.host, port=settings.port, reload=True)
