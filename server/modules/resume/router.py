from beanie import PydanticObjectId
from fastapi import APIRouter, Response, status

from modules.account import CurrentUser
from modules.resume import service
from modules.resume.compile import pdf_filename, to_pdf
from modules.resume.models import (
    BaseResume,
    BaseResumeRead,
    BaseResumeStore,
    ResumeRead,
    ResumeStore,
    TailoredResume,
)

router = APIRouter(tags=["resume"])


@router.get("/versions/{job_id}", response_model=list[ResumeRead])
async def list_versions(job_id: PydanticObjectId, user_id: CurrentUser) -> list[TailoredResume]:
    return await service.list_versions(user_id, job_id)


# Declared before `/{jobId}`: a literal path must be matched ahead of the
# parameterised one, or `/base` is read as a job id.
@router.get("/base", response_model=BaseResumeRead)
async def get_base_resume(user_id: CurrentUser) -> BaseResume:
    return await service.get_base_resume(user_id)


@router.get(
    "/base/pdf",
    responses={200: {"content": {"application/pdf": {"schema": {"type": "string", "format": "binary"}}}}},
)
async def download_base_pdf(user_id: CurrentUser) -> Response:
    """The stored .tex compiled, not re-rendered: the PDF has to be the document the
    user is looking at, including anything the model rectified since the last render."""
    resume = await service.get_base_resume(user_id)
    return Response(
        content=await to_pdf(resume.tex),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{pdf_filename(resume.templateName)}"'
        },
    )


@router.put("/base", response_model=BaseResumeRead)
async def save_base_resume(payload: BaseResumeStore, user_id: CurrentUser) -> BaseResume:
    return await service.save_base_resume(user_id, payload)


@router.post("", response_model=ResumeRead, status_code=status.HTTP_201_CREATED)
async def store_resume(payload: ResumeStore, user_id: CurrentUser) -> TailoredResume:
    return await service.store_resume(user_id, payload)


@router.get("/{job_id}", response_model=ResumeRead)
async def get_resume(job_id: PydanticObjectId, user_id: CurrentUser) -> TailoredResume:
    return await service.get_resume(user_id, job_id)
