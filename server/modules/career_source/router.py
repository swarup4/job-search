from beanie import PydanticObjectId
from fastapi import APIRouter, status

from modules.account import CurrentUser
from modules.career_source import service
from modules.career_source.models import (
    CareerSource,
    CareerSourceCreate,
    CareerSourceCreated,
    CareerSourceRead,
    CareerSourceUpdate,
    Platform,
    RunResult,
)

router = APIRouter(tags=["career-source"])


@router.get("", response_model=list[CareerSourceRead])
async def list_sources(
    _: CurrentUser, enabled: bool | None = None, platform: Platform | None = None
) -> list[CareerSource]:
    return await service.list_sources(enabled, platform)


@router.post("", response_model=CareerSourceCreated, status_code=status.HTTP_201_CREATED)
async def create_source(payload: CareerSourceCreate, _: CurrentUser) -> CareerSourceCreated:
    return await service.create_source(payload)


@router.get("/{source_id}", response_model=CareerSourceRead)
async def get_source(source_id: PydanticObjectId, _: CurrentUser) -> CareerSource:
    return await service.get_source(source_id)


@router.patch("/{source_id}", response_model=CareerSourceRead)
async def update_source(
    source_id: PydanticObjectId, payload: CareerSourceUpdate, _: CurrentUser
) -> CareerSource:
    return await service.update_source(source_id, payload)


@router.put("/result/{source_id}", response_model=CareerSourceRead)
async def record_result(
    source_id: PydanticObjectId, payload: RunResult, _: CurrentUser
) -> CareerSource:
    return await service.record_result(source_id, payload)
