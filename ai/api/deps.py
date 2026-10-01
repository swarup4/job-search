"""Who is calling: the dashboard's forwarded bearer token, and whose it is."""

from __future__ import annotations

import hashlib
import time
from typing import Annotated

import httpx
from fastapi import Depends, Header

from config.errors import BadGateway, Unauthorized
from mcp_servers.jobpilot_api import client
from mcp_servers.jobpilot_api.client import JobPilotApiError

# Every request on this tier checks its token. Without this, each one would cost the
# API server a getAccount as well. The price: a token that has just expired is still
# accepted here for up to this long. Harmless — it can only read progress or start a
# run, and a run's first call to the API server is refused.
VERIFIED_FOR = 60.0

# sha256 of a token -> (account id, when the server last confirmed it). Hashed so no
# token sits in memory longer than the request that carried it.
_verified: dict[str, tuple[str, float]] = {}


async def caller(authorization: Annotated[str | None, Header()] = None) -> tuple[str, str]:
    """The forwarded token and whose it is. This tier has no secret to verify a JWT
    with, so it asks the server — which also proves the token still works."""
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise Unauthorized("missing bearer token")

    client.set_token(token)
    key = hashlib.sha256(token.encode()).hexdigest()
    now = time.monotonic()
    cached = _verified.get(key)
    if cached is not None and now - cached[1] < VERIFIED_FOR:
        return token, cached[0]

    try:
        account = await client.get_account()
    except JobPilotApiError as error:
        if error.status == 401:
            raise Unauthorized(error.detail) from error
        raise BadGateway(error.detail) from error
    except httpx.HTTPError as error:
        raise BadGateway("cannot reach the JobPilot API") from error

    # Tokens rotate hourly, so old entries are dropped rather than left to pile up.
    for stale in [k for k, (_, at) in _verified.items() if now - at >= VERIFIED_FOR]:
        del _verified[stale]
    _verified[key] = (account["id"], now)
    return token, account["id"]


Caller = Annotated[tuple[str, str], Depends(caller)]
