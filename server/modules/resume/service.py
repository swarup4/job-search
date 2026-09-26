from datetime import UTC, datetime

from beanie import PydanticObjectId

from config.errors import Conflict, Invalid, NotFound
from modules.application import ApplicationStage, stage_application
from modules.job import JobStatus, JobUpdate, update_job
from modules.match import ReviewState, get_match
from modules.resume.models import BaseResume, BaseResumeStore, ResumeStore, TailoredResume
from modules.template import get_template


class ResumeNotFound(NotFound):
    def __init__(self, job_id: PydanticObjectId) -> None:
        super().__init__(f"no tailored resume for job {job_id}")


class BaseResumeNotFound(NotFound):
    def __init__(self, user_id: PydanticObjectId) -> None:
        super().__init__(f"no default resume for user {user_id}")


class SelectionGateNotPassed(Conflict):
    """FR-7.3 — tailoring before the user answered the interrupt."""


class Fabrication(Invalid):
    """NFR-8 — a keyword in the .tex that the user never checked."""

    def __init__(self, keywords: list[str]) -> None:
        super().__init__(
            "incorporated keywords the user did not select: " + ", ".join(sorted(keywords))
        )


async def store_resume(user_id: PydanticObjectId, payload: ResumeStore) -> TailoredResume:
    match = await get_match(user_id, payload.jobId)

    if match.review.state is not ReviewState.SELECTED:
        raise SelectionGateNotPassed(
            f"job {payload.jobId} is {match.review.state}, not a completed keyword selection"
        )

    # The load-bearing check. The agent may incorporate fewer keywords than the
    # user chose — a selection with no honest place is left out — but never more.
    labels = {keyword.key: keyword.label for keyword in match.missing}
    allowed = {labels[key] for key in match.review.selectedKeys if key in labels}
    invented = [keyword for keyword in payload.incorporated if keyword not in allowed]
    if invented:
        raise Fabrication(invented)

    latest = await _latest(user_id, payload.jobId)
    resume = TailoredResume(
        **payload.model_dump(),
        userId=user_id,
        matchId=match.id,
        selectedKeys=list(match.review.selectedKeys),
        version=1 if latest is None else latest.version + 1,
    )
    await resume.insert()

    await update_job(payload.jobId, JobUpdate(status=JobStatus.TAILORED))
    await stage_application(
        user_id,
        ApplicationStage(jobId=payload.jobId, resumeId=resume.id, texPath=resume.filePath),
    )
    return resume


async def get_resume(user_id: PydanticObjectId, job_id: PydanticObjectId) -> TailoredResume:
    resume = await _latest(user_id, job_id)
    if resume is None:
        raise ResumeNotFound(job_id)
    return resume


async def list_versions(
    user_id: PydanticObjectId, job_id: PydanticObjectId
) -> list[TailoredResume]:
    return (
        await TailoredResume.find(TailoredResume.userId == user_id, TailoredResume.jobId == job_id)
        .sort(-TailoredResume.version)
        .to_list()
    )


async def _latest(user_id: PydanticObjectId, job_id: PydanticObjectId) -> TailoredResume | None:
    return (
        await TailoredResume.find(TailoredResume.userId == user_id, TailoredResume.jobId == job_id)
        .sort(-TailoredResume.version)
        .first_or_none()
    )


# --- the default resume ------------------------------------------------------


async def get_base_resume(user_id: PydanticObjectId) -> BaseResume:
    resume = await BaseResume.find_one(BaseResume.userId == user_id)
    if resume is None:
        raise BaseResumeNotFound(user_id)
    return resume


async def save_base_resume(user_id: PydanticObjectId, payload: BaseResumeStore) -> BaseResume:
    """Upsert: there is one default resume per user, so submitting again replaces it.

    The .tex is stored exactly as posted. `get_template` runs only to reject a
    template id that does not exist and to record the name alongside the id, so the
    picker can show what was chosen without a second read.
    """
    template = await get_template(payload.templateId)

    resume = await BaseResume.find_one(BaseResume.userId == user_id)
    if resume is None:
        resume = BaseResume(
            userId=user_id,
            templateId=template.id,
            templateName=template.name,
            tex=payload.tex,
        )
        await resume.insert()
        return resume

    resume.templateId = template.id
    resume.templateName = template.name
    resume.tex = payload.tex
    resume.updatedAt = datetime.now(UTC)
    await resume.save()
    return resume
