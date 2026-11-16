import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from beanie import PydanticObjectId

from config.errors import NotFound
from modules.job.experience import parse_experience
from modules.job.location import COUNTRY_NAMES, canonical_country, parse_location
from modules.job.models import (
    Job,
    JobCreate,
    JobCreated,
    JobDetailRead,
    JobSearch,
    JobSearchHit,
    JobSearchResult,
    JobUpdate,
)


class JobNotFound(NotFound):
    def __init__(self, job_id: PydanticObjectId) -> None:
        super().__init__(f"job {job_id} not found")


def compute_dedup_hash(payload: JobCreate) -> str:
    """FR-1.4 — the same posting from two boards must collapse to one row.

    A board's own id is the strongest signal, so it wins when there is one. The JD
    prose used to be part of this seed and no longer can be — it lives in
    `job_descriptions`, which is written after the job exists."""
    if payload.refId:
        seed = f"{payload.source}|{payload.refId}".lower()
    else:
        seed = "|".join(
            part.strip().lower() for part in (payload.title, payload.company, payload.location)
        )
    return hashlib.sha256(seed.encode()).hexdigest()


async def create_job(payload: JobCreate) -> JobCreated:
    dedupHash = payload.dedupHash or compute_dedup_hash(payload)

    existing = await Job.find_one(Job.dedupHash == dedupHash)
    if existing is not None:
        return JobCreated(id=existing.id, duplicate=True)

    parsed_country, cities = parse_location(payload.location)
    experience_min, experience_max = parse_experience(payload.experienceBand)
    job = Job(
        **payload.model_dump(exclude={"dedupHash", "country"}),
        country=canonical_country(payload.country) or parsed_country,
        cities=cities,
        experienceMin=experience_min,
        experienceMax=experience_max,
        dedupHash=dedupHash,
    )
    await job.insert()
    return JobCreated(id=job.id, duplicate=False)


async def get_job(job_id: PydanticObjectId) -> Job:
    job = await Job.find_one(Job.id == job_id)
    if job is None:
        raise JobNotFound(job_id)
    return job


@dataclass(frozen=True)
class SearchTargets:
    """One user's saved search targets, as a filter over the shared catalogue."""

    roles: list[str]
    skills: list[str]
    locations: list[str]


def _whole_words(terms: list[str]) -> dict[str, str] | None:
    """A case-insensitive match for any of `terms` standing alone. Bounded on letters
    and digits rather than a word boundary, so "C++", ".NET" and "Node.js" match the
    way discovery matches them."""
    cleaned = [re.escape(term.strip()) for term in terms if term.strip()]
    if not cleaned:
        return None
    return {"$regex": f"(?<![A-Za-z0-9])(?:{'|'.join(cleaned)})(?![A-Za-z0-9])", "$options": "i"}


def _targets_query(targets: SearchTargets) -> list[dict[str, object]]:
    """The rule discovery keeps a posting by: its title has a role or it names a skill,
    and it is in one of the locations. The skill is read from `techStack`, so a posting
    nobody has read yet matches on its title only. A posting whose country could not be
    read is kept: silence is not a mismatch."""
    clauses: list[dict[str, object]] = []
    wanted: list[dict[str, object]] = []
    roles, skills = _whole_words(targets.roles), _whole_words(targets.skills)
    if roles:
        wanted.append({"title": roles})
    if skills:
        wanted.append({"techStack": skills})
    if wanted:
        clauses.append({"$or": wanted})
    places = _whole_words(targets.locations)
    if places:
        clauses.append(
            {
                "$or": [
                    {"location": places},
                    {"country": places},
                    {"cities": places},
                    {"country": None},
                ]
            }
        )
    return clauses


def _query(
    company: str | None,
    exclude: list[PydanticObjectId] | None,
    targets: SearchTargets | None = None,
) -> dict[str, object]:
    query: dict[str, object] = {}
    if company:
        query["company"] = company
    if exclude:
        query["_id"] = {"$nin": exclude}
    if targets is not None:
        clauses = _targets_query(targets)
        if clauses:
            query["$and"] = clauses
    return query


async def list_jobs(
    company: str | None = None,
    limit: int = 50,
    skip: int = 0,
    exclude: list[PydanticObjectId] | None = None,
    targets: SearchTargets | None = None,
) -> list[Job]:
    """Newest first. `exclude` is how another module asks for the jobs a user has not
    touched — the ones they applied to, or the ones already scored. `targets` keeps
    only the jobs inside one user's search targets."""
    return (
        await Job.find(_query(company, exclude, targets))
        .sort(-Job.discoveredAt)
        .skip(skip)
        .limit(limit)
        .to_list()
    )


async def count_jobs(
    exclude: list[PydanticObjectId] | None = None, targets: SearchTargets | None = None
) -> int:
    return await Job.find(_query(None, exclude, targets)).count()


async def get_job_detail(job_id: PydanticObjectId, user_id: PydanticObjectId) -> JobDetailRead:
    """The job, its description, and the caller's own match and shortlist, in one query.

    One of two places the job module reads other modules' collections (search is the
    other), so the details page costs one round trip instead of three. The match and
    the application are filtered on the caller: the posting is shared, those are not.
    The projection leaves out the embedding (~20 KB of floats) and the unused
    `htmlString`. A job with no description still comes back, with `description`
    null — "no description" is not "no job"."""
    rows = await Job.aggregate(
        [
            {"$match": {"_id": job_id}},
            {
                "$lookup": {
                    "from": "job_descriptions",
                    "localField": "_id",
                    "foreignField": "jobId",
                    "as": "description",
                    "pipeline": [
                        {
                            "$project": {
                                "_id": 0,
                                "id": "$_id",
                                "url": 1,
                                "pageTitle": 1,
                                "jdText": 1,
                                "links": 1,
                                "capturedAt": 1,
                            }
                        }
                    ],
                }
            },
            {"$unwind": {"path": "$description", "preserveNullAndEmptyArrays": True}},
            {
                "$lookup": {
                    "from": "matches",
                    "localField": "_id",
                    "foreignField": "jobId",
                    "as": "match",
                    "pipeline": [
                        {"$match": {"userId": user_id}},
                        {"$addFields": {"id": "$_id"}},
                        {"$project": {"_id": 0, "userId": 0, "jobId": 0}},
                    ],
                }
            },
            {"$unwind": {"path": "$match", "preserveNullAndEmptyArrays": True}},
            {
                "$lookup": {
                    "from": "applications",
                    "localField": "_id",
                    "foreignField": "jobId",
                    "as": "application",
                    # Shortlisted means a row of yours that you have not withdrawn.
                    "pipeline": [
                        {"$match": {"userId": user_id, "status": {"$ne": "withdrawn"}}},
                        {"$project": {"_id": 1}},
                    ],
                }
            },
            {"$addFields": {"shortlisted": {"$gt": [{"$size": "$application"}, 0]}}},
            {"$project": {"dedupHash": 0, "application": 0}},
        ]
    ).to_list()
    if not rows:
        raise JobNotFound(job_id)
    row = rows[0]
    row["id"] = row.pop("_id")
    return JobDetailRead(**row)


async def update_job(job_id: PydanticObjectId, payload: JobUpdate) -> Job:
    job = await get_job(job_id)
    changes = payload.model_dump(exclude_none=True)
    if not changes:
        return job

    for field, value in changes.items():
        setattr(job, field, value)
    if "experienceBand" in changes:
        # The numbers follow the text they were read from, never the other way round.
        job.experienceMin, job.experienceMax = parse_experience(job.experienceBand)
    job.updatedAt = datetime.now(UTC)
    await job.save()
    return job


async def search_jobs(user_id: PydanticObjectId, filters: JobSearch) -> JobSearchResult:
    """Each filled field adds one Mongo condition. The description text lives in
    `job_descriptions`, so keywords first ask it which job ids mention every word.

    Each job on the page then joins the caller's own match and application, so the
    screen gets the score and the shortlist in the same answer."""
    db = Job.get_pymongo_collection().database
    conditions: list[dict[str, object]] = []

    keywords = [word for word in filters.keywords if word]
    if keywords:
        # "Python" and "MongoDB": a description must mention both.
        described = await db.job_descriptions.distinct(
            "jobId", {"$and": [{"jdText": like(word)} for word in keywords]}
        )
        conditions.append({"_id": {"$in": described}})
    if filters.company:
        conditions.append({"company": like(filters.company)})
    if filters.location:
        conditions.append({"location": like(filters.location)})
    if filters.title:
        conditions.append({"title": like(filters.title)})
    if filters.postedWithin:
        since = datetime.now(UTC) - timedelta(days=filters.postedWithin)
        # A board that gave no posting date is judged by when discovery found the job.
        conditions.append(
            {
                "$or": [
                    {"postedAt": {"$gte": since}},
                    {"postedAt": None, "discoveredAt": {"$gte": since}},
                ]
            }
        )

    query = {"$and": conditions} if conditions else {}
    # Paged before the joins, so they run for this page's jobs only.
    rows = await Job.aggregate(
        [
            {"$match": query},
            {"$sort": {"discoveredAt": -1}},
            {"$skip": filters.skip},
            {"$limit": filters.limit},
            {
                "$lookup": {
                    "from": "matches",
                    "localField": "_id",
                    "foreignField": "jobId",
                    "pipeline": [{"$match": {"userId": user_id}}],
                    "as": "match",
                }
            },
            {
                "$lookup": {
                    "from": "applications",
                    "localField": "_id",
                    "foreignField": "jobId",
                    "pipeline": [{"$match": {"userId": user_id}}],
                    "as": "application",
                }
            },
        ]
    ).to_list()
    return JobSearchResult(
        indexed=await Job.find().count(),
        total=await Job.find(query).count(),
        jobs=[_hit(row) for row in rows],
    )


def _hit(row: dict[str, Any]) -> JobSearchHit:
    match = row["match"][0] if row["match"] else None
    application = row["application"][0] if row["application"] else None
    return JobSearchHit(
        **{key: value for key, value in row.items() if key in JobSearchHit.model_fields},
        id=row["_id"],
        score=match["score"] if match else None,
        riskCount=len(match["risks"]) if match else 0,
        presentCount=len(match["present"]) if match else 0,
        missingCount=len(match["missing"]) if match else 0,
        shortlisted=application is not None and application["status"] != "withdrawn",
    )


def like(text: str) -> dict[str, str]:
    """A case-insensitive SQL-style LIKE '%text%'. `re.escape` keeps "C++" a literal
    rather than a broken pattern Mongo would refuse."""
    return {"$regex": re.escape(text), "$options": "i"}


async def locations() -> list[str]:
    """Place names for the Locations box: every city in the stored jobs, most common
    first, then every country — so a suggestion is either somewhere jobs are, or a
    country the location parser recognises."""
    rows = await Job.aggregate(
        [
            {"$unwind": "$cities"},
            {"$group": {"_id": "$cities", "n": {"$sum": 1}}},
            {"$sort": {"n": -1}},
        ]
    ).to_list()
    cities = [row["_id"] for row in rows]
    return cities + sorted(set(COUNTRY_NAMES.values()) - set(cities))
