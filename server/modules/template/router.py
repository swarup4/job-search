from typing import Annotated

from beanie import PydanticObjectId
from fastapi import APIRouter, File, Form, Query, UploadFile, status
from fastapi.responses import FileResponse

from modules.profile import get_resume
from modules.template import service
from modules.template.models import (
    RenderedResume,
    Template,
    TemplateRead,
    TemplateSource,
    TemplateUpdate,
)

router = APIRouter(tags=["template"])


def _read(template: Template) -> TemplateRead:
    return TemplateRead(
        id=template.id,
        name=template.name,
        style=template.style,
        tokens=template.tokens,
        has_preview=template.preview_path is not None,
        status=template.status,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


@router.get("/render/{template_id}/{user_id}", response_model=RenderedResume)
async def render_template(
    template_id: PydanticObjectId, user_id: PydanticObjectId
) -> RenderedResume:
    template = await service.get_template(template_id)
    return RenderedResume(
        id=template.id,
        name=template.name,
        filename=service.tex_filename(template.name),
        tex=service.render(template, await get_resume(user_id)),
    )


@router.get("/preview/{template_id}")
async def template_preview(template_id: PydanticObjectId) -> FileResponse:
    template = await service.get_template(template_id)
    if template.preview_path is None:
        raise service.TemplateNotFound(f"{template_id} preview")
    return FileResponse(template.preview_path, media_type="image/png")


@router.get("", response_model=list[TemplateRead])
async def list_templates(
    # Omitted returns every template; ?status=true is the picker's call.
    template_status: Annotated[bool | None, Query(alias="status")] = None,
) -> list[TemplateRead]:
    return [_read(template) for template in await service.list_templates(template_status)]


@router.post("/upload", response_model=TemplateRead, status_code=status.HTTP_201_CREATED)
async def upload_template(
    tex: Annotated[UploadFile, File(description=".tex source carrying {{TOKEN}} placeholders")],
    name: Annotated[str | None, Form(max_length=60)] = None,
    preview: Annotated[UploadFile | None, File(description="optional PNG")] = None,
) -> TemplateRead:
    """The layout is read from the .tex itself, so the upload is the file and
    little else. A `%%! skills=grid location=city` line in the .tex overrides it."""
    raw = await tex.read()
    try:
        source = raw.decode()
    except UnicodeDecodeError as exc:
        raise service.TemplateRejected("the .tex must be UTF-8 text") from exc

    template = await service.create_template(
        name=name or service.name_from_filename(tex.filename),
        source=source,
        preview=await preview.read() if preview is not None else None,
    )
    return _read(template)


@router.get("/getTemplate/{template_id}", response_model=TemplateSource)
async def get_template(template_id: PydanticObjectId) -> TemplateSource:
    template = await service.get_template(template_id)
    return TemplateSource(**_read(template).model_dump(), tex=template.tex)


@router.patch("/updateTemplate/{template_id}", response_model=TemplateRead)
async def update_template(template_id: PydanticObjectId, payload: TemplateUpdate) -> TemplateRead:
    return _read(await service.update_template(template_id, payload))
