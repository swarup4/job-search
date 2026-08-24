from __future__ import annotations

from datetime import UTC, datetime, timedelta

from beanie import PydanticObjectId

from modules.application.models import (
    AnswerBank,
    Application,
    ApplicationFill,
    ApplicationStage,
    ApplicationStatus,
    StatusTransition,
)


class ApplicationNotFound(Exception):
    def __init__(self, application_id: PydanticObjectId) -> None:
        super().__init__(f"application {application_id} not found")
        self.application_id = application_id


class SubmitNotConfirmed(Exception):
    """FR-5.3 / NFR-7 — nothing may report itself as submitted on its own."""


async def stage_application(payload: ApplicationStage) -> Application:
    existing = await Application.find_one(
        Application.job_id == payload.job_id,
        Application.status == ApplicationStatus.STAGED,
    )
    if existing is not None:
        existing.resume_id = payload.resume_id
        existing.tex_path = payload.tex_path
        existing.ats = payload.ats
        existing.apply_url = payload.apply_url
        await existing.save()
        return existing

    application = Application(**payload.model_dump())
    await application.insert()
    return application


async def get_application(application_id: PydanticObjectId) -> Application:
    application = await Application.get(application_id)
    if application is None:
        raise ApplicationNotFound(application_id)
    return application


async def get_for_job(job_id: PydanticObjectId) -> Application | None:
    return (
        await Application.find(Application.job_id == job_id)
        .sort(-Application.staged_at)
        .first_or_none()
    )


async def list_applications(status: ApplicationStatus | None = None) -> list[Application]:
    query = {"status": status} if status else {}
    return await Application.find(query).sort(-Application.staged_at).to_list()


async def record_fill(application_id: PydanticObjectId, payload: ApplicationFill) -> Application:
    """The extension reports what it filled and highlighted. Status does not move —
    only the user pressing Submit moves it."""
    application = await get_application(application_id)
    application.fields_filled = payload.fields_filled
    application.screening_answers = payload.screening_answers
    await application.save()
    return application


async def set_status(
    application_id: PydanticObjectId,
    payload: StatusTransition,
    follow_up_days: int = 5,
) -> Application:
    application = await get_application(application_id)

    if payload.status is ApplicationStatus.APPLIED and not payload.confirmed_by_user:
        raise SubmitNotConfirmed(
            "an application becomes APPLIED only when the user confirms they submitted it"
        )

    now = datetime.now(UTC)
    application.status = payload.status
    application.last_activity_at = now
    application.last_activity_note = payload.note

    if payload.status is ApplicationStatus.APPLIED:
        application.approved_by_user = True
        application.submitted_at = now
        application.follow_up_due_at = now + timedelta(days=follow_up_days)

    if payload.status in (ApplicationStatus.REJECTED, ApplicationStatus.WITHDRAWN):
        application.follow_up_due_at = None

    await application.save()
    return application


async def due_for_follow_up(now: datetime | None = None) -> list[Application]:
    moment = now or datetime.now(UTC)
    return await Application.find(
        Application.follow_up_due_at != None,
        Application.follow_up_due_at <= moment,
    ).to_list()


async def staged_count() -> int:
    return await Application.find(Application.status == ApplicationStatus.STAGED).count()


async def list_answer_bank() -> list[AnswerBank]:
    return await AnswerBank.find_all().sort(-AnswerBank.used_count).to_list()


async def upsert_answer(key: str, question: str, answer: str, tags: list[str]) -> AnswerBank:
    entry = await AnswerBank.find_one(AnswerBank.key == key)
    if entry is None:
        entry = AnswerBank(key=key, question=question, answer=answer, tags=tags)
    else:
        entry.question = question
        entry.answer = answer
        entry.tags = tags
        entry.updated_at = datetime.now(UTC)
    await entry.save()
    return entry
