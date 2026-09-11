"""The correlation id shared by every middleware and by the error responses.

Assignment is idempotent so the middlewares stay independent of each other's order —
whichever runs first assigns it, the rest read it back.
"""

import uuid

from fastapi import Request

REQUEST_ID_HEADER = "X-Request-ID"


def request_id(request: Request) -> str:
    existing: str | None = getattr(request.state, "request_id", None)
    if existing is not None:
        return existing

    # An id supplied by the caller wins, so one dashboard action can be traced
    # across the several requests it fans out into.
    value = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex[:12]
    request.state.request_id = value
    return value
