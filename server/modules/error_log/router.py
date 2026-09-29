from typing import Annotated

from fastapi import APIRouter, Query, status

from modules.account import CurrentUser
from modules.error_log import service
from modules.error_log.models import ErrorEntry, ErrorReport

router = APIRouter(tags=["errorLog"])


@router.get("", response_model=list[ErrorEntry])
async def list_errors(
    _: CurrentUser, limit: Annotated[int, Query(ge=1, le=1000)] = 200
) -> list[ErrorEntry]:
    return await service.list_errors(limit)


@router.post("", status_code=status.HTTP_204_NO_CONTENT)
async def report_error(payload: ErrorReport, _: CurrentUser) -> None:
    await service.report_error(payload)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def clear_errors(_: CurrentUser) -> None:
    await service.clear_errors()
