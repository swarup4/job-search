"""The app, pointed at a throwaway database.

Local MongoDB is already a dev prerequisite, so the suite drives real queries
against `jobpilot_test` rather than mocking the driver — see server-api.md. The
database is dropped between runs, and no test reaches Atlas or Voyage, neither of
which belongs to this tier.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from config.database import connect, disconnect
from main import create_app

TEST_DB = "jobpilot_test"

# Forced local, not whatever `server/.env` points at. server-api.md says these tests
# must never reach Atlas, and a suite that creates and drops a database should not be
# doing it over the network on someone's cluster. `TEST_MONGODB_URI` overrides.
os.environ["MONGODB_URI"] = os.environ.get("TEST_MONGODB_URI", "mongodb://127.0.0.1:27017")


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    database = await connect(TEST_DB)
    for name in await database.list_collection_names():
        await database[name].delete_many({})

    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test/api") as http:
        yield http

    await database.client.drop_database(TEST_DB)
    await disconnect()


@pytest.fixture
async def signed_in(client: AsyncClient) -> AsyncClient:
    """A client carrying a real token. No route outside signup/login accepts less."""
    response = await client.post(
        "/account/signup",
        json={"name": "Test User", "email": "test@example.com", "password": "correct-horse"},
    )
    assert response.status_code == 201, response.text
    client.headers["Authorization"] = f"Bearer {response.json()['accessToken']}"
    return client
