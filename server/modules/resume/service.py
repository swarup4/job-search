from beanie import PydanticObjectId

from errors import Conflict, Invalid, NotFound
from modules.application import ApplicationStage, stage_application
from modules.job import JobStatus, JobUpdate, update_job
from modules.match import ReviewState, get_match
from modules.resume.models import ResumeStore, TailoredResume


class ResumeNotFound(NotFound):
    def __init__(self, job_id: PydanticObjectId) -> None:
        super().__init__(f"no tailored resume for job {job_id}")


class SelectionGateNotPassed(Conflict):
    """FR-7.3 — tailoring before the user answered the interrupt."""


class Fabrication(Invalid):
    """NFR-8 — a keyword in the .tex that the user never checked."""

    def __init__(self, keywords: list[str]) -> None:
        super().__init__(
            "incorporated keywords the user did not select: " + ", ".join(sorted(keywords))
        )


async def store_resume(payload: ResumeStore) -> TailoredResume:
    match = await get_match(payload.job_id)

    if match.review.state is not ReviewState.SELECTED:
        raise SelectionGateNotPassed(
            f"job {payload.job_id} is {match.review.state}, not a completed keyword selection"
        )

    # The load-bearing check. The agent may incorporate fewer keywords than the
    # user chose — a selection with no honest place is left out — but never more.
    labels = {keyword.key: keyword.label for keyword in match.missing}
    allowed = {labels[key] for key in match.review.selected_keys if key in labels}
    invented = [keyword for keyword in payload.incorporated if keyword not in allowed]
    if invented:
        raise Fabrication(invented)

    latest = await _latest(payload.job_id)
    resume = TailoredResume(
        **payload.model_dump(),
        match_id=match.id,
        selected_keys=list(match.review.selected_keys),
        version=1 if latest is None else latest.version + 1,
    )
    await resume.insert()

    await update_job(payload.job_id, JobUpdate(status=JobStatus.TAILORED))
    await stage_application(
        ApplicationStage(job_id=payload.job_id, resume_id=resume.id, tex_path=resume.file_path)
    )
    return resume


async def get_resume(job_id: PydanticObjectId) -> TailoredResume:
    resume = await _latest(job_id)
    if resume is None:
        raise ResumeNotFound(job_id)
    return resume


async def list_versions(job_id: PydanticObjectId) -> list[TailoredResume]:
    return (
        await TailoredResume.find(TailoredResume.job_id == job_id)
        .sort(-TailoredResume.version)
        .to_list()
    )


async def _latest(job_id: PydanticObjectId) -> TailoredResume | None:
    return (
        await TailoredResume.find(TailoredResume.job_id == job_id)
        .sort(-TailoredResume.version)
        .first_or_none()
    )
