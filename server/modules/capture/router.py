from beanie import PydanticObjectId
from fastapi import APIRouter, Query, status

from modules.account import CurrentUser
from modules.capture import service
from modules.capture.models import (
    Capture,
    CaptureCreate,
    CaptureCreated,
    CaptureDetail,
    CaptureRead,
    CaptureStatus,
)

router = APIRouter(tags=["capture"])


@router.get("", response_model=list[CaptureRead])
async def list_captures(
    user_id: CurrentUser,
    capture_status: CaptureStatus | None = Query(default=None, alias="status"),
    url: str | None = None,
    limit: int = Query(default=50, le=200),
    skip: int = 0,
) -> list[Capture]:
    return await service.list_captures(user_id, capture_status, url, limit, skip)


@router.post("", response_model=CaptureCreated, status_code=status.HTTP_201_CREATED)
async def create_capture(payload: CaptureCreate, user_id: CurrentUser) -> CaptureCreated:
    return await service.create_capture(user_id, payload)


@router.get("/{capture_id}", response_model=CaptureDetail)
async def get_capture(capture_id: PydanticObjectId, user_id: CurrentUser) -> Capture:
    return await service.get_capture(user_id, capture_id)
