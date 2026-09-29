import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

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
    Badges,
    Board,
    BoardCard,
    BoardColumn,
    BoardCounts,
    ShortlistRow,
    StatusTransition,
    Tracker,
    TrackerRow,
)
from modules.job import Job, count_jobs, get_job
from modules.match import pending_counts

# Before the user reports a submit. Past these, the row records what was actually sent.
PRE_SUBMIT = (ApplicationStatus.SHORTLISTED, ApplicationStatus.STAGED, ApplicationStatus.WITHDRAWN)


class ApplicationNotFound(NotFound):
    def __init__(self, application_id: PydanticObjectId) -> None:
        super().__init__(f"application {application_id} not found")


class SubmitNotConfirmed(Conflict):
    """FR-5.3 / NFR-7 — nothing may report itself as submitted on its own."""


class AlreadySubmitted(Conflict):
    """A submitted application leaves the shortlist through its own status, not the bookmark."""


async def get_for_job(user_id: PydanticObjectId, job_id: PydanticObjectId) -> Application | None:
    return await Application.find_one(Application.userId == user_id, Application.jobId == job_id)


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


# The application columns and the statuses each shows; `applied` folds in `viewed`.
BOARD_COLUMNS: dict[str, list[ApplicationStatus]] = {
    "shortlisted": [ApplicationStatus.SHORTLISTED],
    "staged": [ApplicationStatus.STAGED],
    "applied": [ApplicationStatus.APPLIED, ApplicationStatus.VIEWED],
    "interview": [ApplicationStatus.INTERVIEW],
}


def _your_match(user_id: PydanticObjectId, job_field: str) -> list[dict[str, object]]:
    """Stages joining the caller's match headline onto each row, keyed on `job_field`."""
    return [
        {
            "$lookup": {
                "from": "matches",
                "localField": job_field,
                "foreignField": "jobId",
                "as": "match",
                "pipeline": [
                    {"$match": {"userId": user_id}},
                    {
                        "$project": {
                            "_id": 0,
                            "score": 1,
                            "reviewState": "$review.state",
                            "risk": {"$arrayElemAt": ["$risks.title", 0]},
                        }
                    },
                ],
            }
        },
        {"$unwind": {"path": "$match", "preserveNullAndEmptyArrays": True}},
    ]


def _card(
    job: dict[str, Any], match: dict[str, Any] | None, application: dict[str, Any] | None
) -> BoardCard:
    application = application or {}
    return BoardCard(
        id=job["_id"],
        title=job["title"],
        company=job["company"],
        location=job["location"],
        source=job["source"],
        discoveredAt=job["discoveredAt"],
        **(match or {}),
        texPath=application.get("texPath"),
        stagedAt=application.get("stagedAt"),
        lastActivityAt=application.get("lastActivityAt"),
        lastActivityNote=application.get("lastActivityNote"),
    )


async def _new_cards(
    user_id: PydanticObjectId, started: list[PydanticObjectId], skip: int, limit: int
) -> list[BoardCard]:
    rows = await Job.aggregate(
        [
            {"$match": {"_id": {"$nin": started}}},
            {"$sort": {"discoveredAt": -1}},
            {"$skip": skip},
            {"$limit": limit},
            *_your_match(user_id, "_id"),
        ]
    ).to_list()
    return [_card(row, row.get("match"), None) for row in rows]


async def _application_cards(
    user_id: PydanticObjectId, statuses: list[ApplicationStatus], skip: int, limit: int
) -> list[BoardCard]:
    rows = await Application.aggregate(
        [
            {"$match": {"userId": user_id, "status": {"$in": [s.value for s in statuses]}}},
            # The order `list_applications` has always used.
            {"$sort": {"stagedAt": -1, "shortlistedAt": -1}},
            {"$skip": skip},
            {"$limit": limit},
            {
                "$lookup": {
                    "from": "jobs",
                    "localField": "jobId",
                    "foreignField": "_id",
                    "as": "job",
                }
            },
            {"$unwind": "$job"},
            *_your_match(user_id, "jobId"),
        ]
    ).to_list()
    return [_card(row["job"], row.get("match"), row) for row in rows]


async def board_column(
    user_id: PydanticObjectId, column: str, skip: int, limit: int
) -> list[BoardCard]:
    """One column's cards after the first `skip` — the Pipeline's "Show more"."""
    if column == "new":
        return await _new_cards(user_id, await _started_job_ids(user_id), skip, limit)
    return await _application_cards(user_id, BOARD_COLUMNS[column], skip, limit)


async def board(user_id: PydanticObjectId, limit: int) -> Board:
    """The first `limit` cards of each column, your match joined in. Each column carries
    its own total so "Show more" knows when to stop."""
    started = await _started_job_ids(user_id)
    counts, new, *columns = await asyncio.gather(
        board_counts(user_id),
        _new_cards(user_id, started, 0, limit),
        *(_application_cards(user_id, statuses, 0, limit) for statuses in BOARD_COLUMNS.values()),
    )
    totals = counts.model_dump()
    return Board(
        columns={
            "new": BoardColumn(count=counts.new, cards=new),
            **{
                key: BoardColumn(count=totals[key], cards=cards)
                for key, cards in zip(BOARD_COLUMNS, columns, strict=True)
            },
        },
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


async def badges(user_id: PydanticObjectId) -> Badges:
    waiting = await pending_counts(user_id)
    return Badges(
        keywordSelections=waiting.keywordSelections,
        nextJobId=waiting.nextJobId,
        staged=await Application.find(
            Application.userId == user_id, Application.status == ApplicationStatus.STAGED
        ).count(),
        shortlisted=await Application.find(
            Application.userId == user_id, Application.status == ApplicationStatus.SHORTLISTED
        ).count(),
    )


async def shortlisted_jobs(user_id: PydanticObjectId) -> list[ShortlistRow]:
    """Your shortlisted jobs, newest first, each with its listing and your match counts —
    one query for the Shortlist screen instead of one request per job."""
    rows = await Application.aggregate(
        [
            {"$match": {"userId": user_id, "status": ApplicationStatus.SHORTLISTED.value}},
            {"$sort": {"shortlistedAt": -1}},
            {
                "$lookup": {
                    "from": "jobs",
                    "localField": "jobId",
                    "foreignField": "_id",
                    "as": "job",
                }
            },
            {"$unwind": "$job"},
            {
                "$lookup": {
                    "from": "matches",
                    "localField": "jobId",
                    "foreignField": "jobId",
                    "as": "match",
                    "pipeline": [
                        {"$match": {"userId": user_id}},
                        {
                            "$project": {
                                "_id": 0,
                                "score": 1,
                                "riskCount": {"$size": "$risks"},
                                "presentCount": {"$size": "$present"},
                                "missingCount": {"$size": "$missing"},
                            }
                        },
                    ],
                }
            },
            {"$unwind": {"path": "$match", "preserveNullAndEmptyArrays": True}},
        ]
    ).to_list()

    return [
        ShortlistRow(
            **{key: row["job"].get(key) for key in _SHORTLIST_JOB_FIELDS},
            id=row["job"]["_id"],
            shortlistedAt=row.get("shortlistedAt"),
            **row.get("match", {}),
        )
        for row in rows
    ]


_SHORTLIST_JOB_FIELDS = (
    "title",
    "company",
    "location",
    "source",
    "jobType",
    "workMode",
    "salaryText",
    "postedAt",
    "discoveredAt",
)


async def tracker(user_id: PydanticObjectId) -> Tracker:
    """Shortlisted, staged and submitted applications, each with its job's title, company
    and location from one `$lookup`. A row withdrawn before it was ever submitted is an
    undone shortlist, not an application, and is left out."""
    rows = await Application.aggregate(
        [
            {"$match": {"userId": user_id}},
            {
                "$lookup": {
                    "from": "jobs",
                    "localField": "jobId",
                    "foreignField": "_id",
                    "as": "job",
                }
            },
            {"$unwind": "$job"},
        ]
    ).to_list()

    shortlisted: list[TrackerRow] = []
    staged: list[TrackerRow] = []
    submitted: list[TrackerRow] = []
    for row in rows:
        entry = _tracker_row(row)
        if entry.status is ApplicationStatus.SHORTLISTED:
            shortlisted.append(entry)
        elif entry.status is ApplicationStatus.STAGED:
            staged.append(entry)
        elif entry.submittedAt is not None:
            submitted.append(entry)

    shortlisted.sort(key=lambda entry: _utc(entry.shortlistedAt), reverse=True)
    staged.sort(key=lambda entry: _utc(entry.stagedAt), reverse=True)
    submitted.sort(key=lambda entry: _utc(entry.lastActivityAt or entry.submittedAt), reverse=True)
    return Tracker(shortlisted=shortlisted, staged=staged, submitted=submitted)


_STORED = (
    "jobId",
    "status",
    "ats",
    "applyUrl",
    "texPath",
    "shortlistedAt",
    "stagedAt",
    "submittedAt",
    "lastActivityAt",
    "lastActivityNote",
    "followUpDueAt",
    "followUpSentAt",
)


def _tracker_row(row: dict[str, Any]) -> TrackerRow:
    job = row["job"]
    return TrackerRow(
        # The stored fields that carry over as they are; the rest are joined or counted.
        **{key: row[key] for key in _STORED if key in row},
        id=row["_id"],
        title=job["title"],
        company=job["company"],
        location=job["location"],
        listingUrl=job.get("listingUrl"),
        fieldsFilled=len(row.get("fieldsFilled", [])),
        needsAnswer=sum(
            1 for answer in row.get("screeningAnswers", []) if not answer.get("answer")
        ),
    )


def _utc(moment: datetime | None) -> datetime:
    """Mongo hands back naive UTC datetimes; sorting them beside aware ones needs one
    convention. A missing date sorts last."""
    if moment is None:
        return datetime.min.replace(tzinfo=UTC)
    return moment.replace(tzinfo=UTC) if moment.tzinfo is None else moment
