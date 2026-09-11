"""The last-resort catch for anything a route lets escape.

Domain errors never reach here — `errors.py` converts those further down the stack.
What lands in the `except` is the genuinely unexpected: a bug, a driver fault, a
dropped connection. Without this, Starlette answers those with a plain-text
"Internal Server Error" that the dashboard's axios interceptor cannot read a
message out of.
"""

import logging

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from middleware.context import REQUEST_ID_HEADER, request_id

logger = logging.getLogger("jobpilot.error")


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        try:
            return await call_next(request)
        except Exception:
            correlation_id = request_id(request)
            logger.exception(
                "unhandled error on %s %s [%s]",
                request.method,
                request.url.path,
                correlation_id,
            )
            # `detail` stays a string so the dashboard renders it like any other error.
            response = JSONResponse(
                status_code=500,
                content={"detail": "Internal server error.", "request_id": correlation_id},
            )
            response.headers[REQUEST_ID_HEADER] = correlation_id
            return response
