"""Domain errors, and the one place they become HTTP responses.

A service raises the error that describes what went wrong; the handler registered
in `main.py` turns it into a response. Routers catch nothing.
"""

from fastapi import Request
from fastapi.responses import JSONResponse


class DomainError(Exception):
    status: int = 400


class NotFound(DomainError):
    status = 404


class Conflict(DomainError):
    status = 409


class Invalid(DomainError):
    status = 422


async def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
    # `detail` stays a plain string — the dashboard's axios interceptor reads it directly.
    return JSONResponse(
        status_code=exc.status,
        content={
            "detail": str(exc),
            "request_id": getattr(request.state, "request_id", None),
        },
    )
