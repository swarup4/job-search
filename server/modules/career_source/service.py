from datetime import UTC, datetime

from beanie import PydanticObjectId

from config.errors import Conflict, NotFound
from modules.career_source.models import (
    CareerSource,
    CareerSourceCreate,
    CareerSourceCreated,
    CareerSourceUpdate,
    DiscoverySummary,
    Platform,
    RunResult,
)


class CareerSourceNotFound(NotFound):
    def __init__(self, source_id: PydanticObjectId) -> None:
        super().__init__(f"career source {source_id} not found")


class CareerSourceExists(Conflict):
    def __init__(self, name: str) -> None:
        super().__init__(f"career source {name!r} already exists")


async def create_source(payload: CareerSourceCreate) -> CareerSourceCreated:
    if await CareerSource.find_one(CareerSource.name == payload.name) is not None:
        raise CareerSourceExists(payload.name)

    source = CareerSource(**payload.model_dump())
    await source.insert()
    return CareerSourceCreated(id=source.id)


async def get_source(source_id: PydanticObjectId) -> CareerSource:
    source = await CareerSource.find_one(CareerSource.id == source_id)
    if source is None:
        raise CareerSourceNotFound(source_id)
    return source


async def list_sources(
    enabled: bool | None = None, platform: Platform | None = None
) -> list[CareerSource]:
    query: dict[str, object] = {}
    if enabled is not None:
        query["enabled"] = enabled
    if platform is not None:
        query["platform"] = platform
    return await CareerSource.find(query).sort(+CareerSource.name).to_list()


async def update_source(source_id: PydanticObjectId, payload: CareerSourceUpdate) -> CareerSource:
    source = await get_source(source_id)
    changes = payload.model_dump(exclude_none=True)
    if not changes:
        return source

    for field, value in changes.items():
        setattr(source, field, value)
    source.updatedAt = datetime.now(UTC)
    await source.save()
    return source


async def record_result(source_id: PydanticObjectId, result: RunResult) -> CareerSource:
    source = await get_source(source_id)
    source.lastRunAt = datetime.now(UTC)
    source.lastResult = result
    await source.save()
    return source


async def last_run_summary() -> DiscoverySummary:
    sources = await CareerSource.find({"lastResult": {"$ne": None}}).to_list()
    results = [source.lastResult for source in sources if source.lastResult is not None]
    return DiscoverySummary(
        lastRunAt=max((s.lastRunAt for s in sources if s.lastRunAt), default=None),
        companies=len(results),
        ok=sum(1 for r in results if not r.blocked and not r.error and not r.failed),
        failed=sum(1 for r in results if not r.blocked and (r.error or r.failed)),
        blocked=sum(1 for r in results if r.blocked),
        newJobs=sum(r.new for r in results),
    )
