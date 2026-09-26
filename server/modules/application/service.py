from datetime import UTC, datetime, timedelta

from beanie import PydanticObjectId

from config.errors import Conflict, NotFound
from modules.application.models import (
    AnswerBank,
    ApplicantFields,
    ApplicantProfile,
    Application,
    ApplicationFill,
    ApplicationStage,
    ApplicationStatus,
    BoardCounts,
    StatusTransition,
)
from modules.job import Job, count_jobs, get_job, list_jobs

# Before the user reports a submit. Past these, the row records what was actually sent.
PRE_SUBMIT = (ApplicationStatus.SHORTLISTED, ApplicationStatus.STAGED, ApplicationStatus.WITHDRAWN)


class ApplicationNotFound(NotFound):
    def __init__(self, application_id: PydanticObjectId) -> None:
        super().__init__(f"application {application_id} not found")


class SubmitNotConfirmed(Conflict):
    """FR-5.3 / NFR-7 — nothing may report itself as submitted on its own."""


class AlreadySubmitted(Conflict):
    """A submitted application leaves the shortlist through its own status, not the bookmark."""


async def shortlist(user_id: PydanticObjectId, job_id: PydanticObjectId) -> Application:
    """Starts the user's work on a job. A repeat returns the row as it is; a withdrawn
    row comes back as shortlisted."""
    await get_job(job_id)
    application = await get_for_job(user_id, job_id)
    if application is None:
        application = Application(userId=user_id, jobId=job_id)
        await application.insert()
        return application

    if application.status is ApplicationStatus.WITHDRAWN:
        application.status = ApplicationStatus.SHORTLISTED
        application.shortlistedAt = datetime.now(UTC)
        await application.save()
    return application


async def unshortlist(user_id: PydanticObjectId, job_id: PydanticObjectId) -> Application | None:
    """An untouched row is deleted, so the job goes back to New. Once a resume hangs off
    it the row is kept, withdrawn. None means it was deleted, or never existed."""
    application = await get_for_job(user_id, job_id)
    if application is None:
        return None
    if application.status not in PRE_SUBMIT:
        raise AlreadySubmitted(
            f"job {job_id} was submitted; change the application's status instead"
        )

    if application.status is ApplicationStatus.SHORTLISTED and application.resumeId is None:
        await application.delete()
        return None

    application.status = ApplicationStatus.WITHDRAWN
    application.lastActivityAt = datetime.now(UTC)
    application.lastActivityNote = "Removed from shortlist"
    await application.save()
    return application


async def stage_application(user_id: PydanticObjectId, payload: ApplicationStage) -> Application:
    """A tailored resume stages the user's one row for this job, creating it when the job
    was never shortlisted. Re-tailoring after a submit stores the resume version only:
    the row keeps the .tex that was actually sent."""
    application = await get_for_job(user_id, payload.jobId)
    if application is None:
        application = Application(userId=user_id, jobId=payload.jobId)
    elif application.status not in PRE_SUBMIT:
        return application

    for field, value in payload.model_dump().items():
        setattr(application, field, value)
    application.status = ApplicationStatus.STAGED
    application.stagedAt = datetime.now(UTC)
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
    return await Application.find_one(Application.userId == user_id, Application.jobId == job_id)


async def list_applications(
    user_id: PydanticObjectId, statuses: list[ApplicationStatus] | None = None
) -> list[Application]:
    query: dict[str, object] = {"userId": user_id}
    if statuses:
        query["status"] = {"$in": statuses}
    return (
        await Application.find(query)
        .sort(-Application.stagedAt, -Application.shortlistedAt)
        .to_list()
    )


async def _started_job_ids(user_id: PydanticObjectId) -> list[PydanticObjectId]:
    rows = await Application.find(Application.userId == user_id).to_list()
    return [row.jobId for row in rows]


async def unstarted_jobs(user_id: PydanticObjectId, limit: int, skip: int) -> list[Job]:
    """The New column: jobs this user has no application for, newest first."""
    return await list_jobs(limit=limit, skip=skip, exclude=await _started_job_ids(user_id))


async def board_counts(user_id: PydanticObjectId) -> BoardCounts:
    rows = await Application.aggregate(
        [{"$match": {"userId": user_id}}, {"$group": {"_id": "$status", "n": {"$sum": 1}}}]
    ).to_list()
    by_status = {row["_id"]: row["n"] for row in rows}
    return BoardCounts(
        new=await count_jobs(exclude=await _started_job_ids(user_id)),
        shortlisted=by_status.get(ApplicationStatus.SHORTLISTED, 0),
        staged=by_status.get(ApplicationStatus.STAGED, 0),
        applied=by_status.get(ApplicationStatus.APPLIED, 0)
        + by_status.get(ApplicationStatus.VIEWED, 0),
        interview=by_status.get(ApplicationStatus.INTERVIEW, 0),
    )


async def record_fill(
    user_id: PydanticObjectId, application_id: PydanticObjectId, payload: ApplicationFill
) -> Application:
    """The extension reports what it filled and highlighted. Status does not move —
    only the user pressing Submit moves it."""
    application = await get_application(user_id, application_id)
    application.fieldsFilled = payload.fieldsFilled
    application.screeningAnswers = payload.screeningAnswers
    await application.save()
    return application


async def set_status(
    user_id: PydanticObjectId,
    application_id: PydanticObjectId,
    payload: StatusTransition,
    follow_up_days: int = 5,
) -> Application:
    application = await get_application(user_id, application_id)

    if payload.status is ApplicationStatus.APPLIED and not payload.confirmedByUser:
        raise SubmitNotConfirmed(
            "an application becomes APPLIED only when the user confirms they submitted it"
        )

    now = datetime.now(UTC)
    application.status = payload.status
    application.lastActivityAt = now
    application.lastActivityNote = payload.note

    if payload.status is ApplicationStatus.APPLIED:
        application.approvedByUser = True
        application.submittedAt = now
        application.followUpDueAt = now + timedelta(days=follow_up_days)

    if payload.status in (ApplicationStatus.REJECTED, ApplicationStatus.WITHDRAWN):
        application.followUpDueAt = None

    await application.save()
    return application


async def due_for_follow_up(
    user_id: PydanticObjectId, now: datetime | None = None
) -> list[Application]:
    moment = now or datetime.now(UTC)
    return await Application.find(
        {"userId": user_id, "followUpDueAt": {"$ne": None, "$lte": moment}},
    ).to_list()


async def staged_count(user_id: PydanticObjectId) -> int:
    return await Application.find(
        Application.userId == user_id, Application.status == ApplicationStatus.STAGED
    ).count()


async def list_answer_bank(user_id: PydanticObjectId) -> list[AnswerBank]:
    return await AnswerBank.find(AnswerBank.userId == user_id).sort(-AnswerBank.usedCount).to_list()


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
        entry.updatedAt = datetime.now(UTC)
    await entry.save()
    return entry


async def get_applicant(user_id: PydanticObjectId) -> ApplicantProfile:
    """An unsaved profile reads back empty rather than 404. Nothing is saved until
    the user fills the form in, and the extension asks for this on every fill —
    "you have not filled this in yet" is the normal first answer, not an error."""
    stored = await ApplicantProfile.find_one(ApplicantProfile.userId == user_id)
    return stored or ApplicantProfile(userId=user_id)


async def save_applicant(user_id: PydanticObjectId, payload: ApplicantFields) -> ApplicantProfile:
    """Upsert, and a full replace: one per user, and the Settings form posts the
    whole thing, so an omitted field means the user cleared it."""
    stored = await ApplicantProfile.find_one(ApplicantProfile.userId == user_id)

    if stored is None:
        stored = ApplicantProfile(**payload.model_dump(), userId=user_id)
        await stored.insert()
        return stored

    for field, value in payload.model_dump().items():
        setattr(stored, field, value)
    stored.updatedAt = datetime.now(UTC)
    await stored.save()
    return stored
