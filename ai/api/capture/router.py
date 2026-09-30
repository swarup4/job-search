from __future__ import annotations

from fastapi import APIRouter

from api.capture import service
from api.capture.models import CaptureResult
from api.deps import Caller

router = APIRouter(tags=["capture"])


@router.post("/{description_id}", response_model=CaptureResult)
async def process_capture(description_id: str, _: Caller) -> CaptureResult:
    return await service.process_capture(description_id)
