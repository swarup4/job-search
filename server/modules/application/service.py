from datetime import UTC, datetime, timedelta

from beanie import PydanticObjectId

from config.errors import Conflict, NotFound
from modules.application.models import (
    AnswerBank,
    Application,
    ApplicationFill,
    ApplicationStage,
    ApplicationStatus,
    StatusTransition,
)


class ApplicationNotFound(NotFound):
    def __init__(self, application_id: PydanticObjectId) -> None:
        super().__init__(f"application {application_id} not found")


class SubmitNotConfirmed(Conflict):
    """FR-5.3 / NFR-7 — nothing may report itself as submitted on its own."""


async def stage_application(user_id: PydanticObjectId, payload: ApplicationStage) -> Application:
    """Re-tailoring a job updates the staged application rather than adding a second one."""
    application = await Application.find_one(
        Application.userId == user_id,
        Application.job_id == payload.job_id,
        Application.status == ApplicationStatus.STAGED,
    )
    if application is None:
        application = Application(**payload.model_dump(), userId=user_id)
        await application.insert()
        return application

    for field, value in payload.model_dump().items():
        setattr(application, field, value)
    await application.save()
    return application


async def get_application(
    user_id: PydanticObjectId, application_id: PydanticObjectId
) -> Application:
    application = await Application.find_one(
        Application.id == application_id, Application.userId == user_id
    )
    if application is None:
        raise ApplicationNotFound(application_id)
    return application


async def get_for_job(user_id: PydanticObjectId, job_id: PydanticObjectId) -> Application | None:
    return (
        await Application.find(Application.userId == user_id, Application.job_id == job_id)
        .sort(-Application.staged_at)
        .first_or_none()
    )


async def list_applications(
    user_id: PydanticObjectId, status: ApplicationStatus | None = None
) -> list[Application]:
    query: dict[str, object] = {"userId": user_id}
    if status:
        query["status"] = status
    return await Application.find(query).sort(-Application.staged_at).to_list()


async def record_fill(
    user_id: PydanticObjectId, application_id: PydanticObjectId, payload: ApplicationFill
) -> Application:
    """The extension reports what it filled and highlighted. Status does not move —
    only the user pressing Submit moves it."""
    application = await get_application(user_id, application_id)
    application.fields_filled = payload.fields_filled
    application.screening_answers = payload.screening_answers
    await application.save()
    return application


async def set_status(
    user_id: PydanticObjectId,
    application_id: PydanticObjectId,
    payload: StatusTransition,
    follow_up_days: int = 5,
) -> Application:
    application = await get_application(user_id, application_id)

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


async def due_for_follow_up(
    user_id: PydanticObjectId, now: datetime | None = None
) -> list[Application]:
    moment = now or datetime.now(UTC)
    return await Application.find(
        {"userId": user_id, "follow_up_due_at": {"$ne": None, "$lte": moment}},
    ).to_list()


async def staged_count(user_id: PydanticObjectId) -> int:
    return await Application.find(
        Application.userId == user_id, Application.status == ApplicationStatus.STAGED
    ).count()


async def list_answer_bank(user_id: PydanticObjectId) -> list[AnswerBank]:
    return (
        await AnswerBank.find(AnswerBank.userId == user_id).sort(-AnswerBank.used_count).to_list()
    )


async def upsert_answer(
    user_id: PydanticObjectId, key: str, question: str, answer: str, tags: list[str]
) -> AnswerBank:
    entry = await AnswerBank.find_one(AnswerBank.userId == user_id, AnswerBank.key == key)
    if entry is None:
        entry = AnswerBank(userId=user_id, key=key, question=question, answer=answer, tags=tags)
    else:
        entry.question = question
        entry.answer = answer
        entry.tags = tags
        entry.updated_at = datetime.now(UTC)
    await entry.save()
    return entry
