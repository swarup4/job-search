from __future__ import annotations

from typing import Any

from fastapi import APIRouter, status

from api.deps import Caller
from api.tailoring import service

router = APIRouter(tags=["tailoring"])


@router.post("/{job_id}", status_code=status.HTTP_201_CREATED)
async def tailor(job_id: str, _: Caller) -> dict[str, Any]:
    return await service.tailor(job_id)
