"""One line per request: what was asked, what came back, how long it took."""

import logging
import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from middleware.context import REQUEST_ID_HEADER, request_id

logger = logging.getLogger("jobpilot.access")


class AccessLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        correlation_id = request_id(request)
        started = time.perf_counter()

        response = await call_next(request)

        logger.log(
            logging.WARNING if response.status_code >= 500 else logging.INFO,
            "%s %s %d %.1fms [%s]",
            request.method,
            request.url.path,
            response.status_code,
            (time.perf_counter() - started) * 1000,
            correlation_id,
        )
        response.headers[REQUEST_ID_HEADER] = correlation_id
        return response
