"""Domain errors, and the one place they become HTTP responses.

A service raises the error that describes what went wrong; the handler registered
in `main.py` turns it into a response. Routers catch nothing.
"""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse


class DomainError(Exception):
    status: int = 400


class Unauthorized(DomainError):
    status = 401


class Conflict(DomainError):
    status = 409


class Invalid(DomainError):
    status = 422


class BadGateway(DomainError):
    status = 502


class Upstream(DomainError):
    """The API server refused. Its status passes through, except that a 5xx is its
    failure, not the caller's, and so becomes a 502 here."""

    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status if status < 500 else 502


async def handle_domain_error(_: Request, exc: DomainError) -> JSONResponse:
    # `detail` stays a plain string — the dashboard's axios interceptor reads it directly.
    return JSONResponse(status_code=exc.status, content={"detail": str(exc)})
