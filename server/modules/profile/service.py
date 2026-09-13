from datetime import UTC, datetime

from beanie import PydanticObjectId

from config.errors import Conflict, NotFound
from modules.account import Account
from modules.profile.models import (
    Certification,
    CertificationFields,
    CertificationRead,
    Education,
    EducationFields,
    EducationRead,
    Experience,
    ExperienceFields,
    ExperienceRead,
    Profile,
    ProfileFields,
    ProfileRead,
    Skill,
    SkillFields,
    SkillRead,
    UserProfile,
)


class ProfileNotFound(NotFound):
    """No profile for this account — the user has not filled in My details."""


class ProfileExists(Conflict):
    """One profile per account — it is created once, then edited."""


class UnknownUser(NotFound):
    def __init__(self, user_id: PydanticObjectId) -> None:
        super().__init__(f"account {user_id} not found")


class ExperienceNotFound(NotFound):
    def __init__(self, entry_id: PydanticObjectId) -> None:
        super().__init__(f"experience {entry_id} not found")


class EducationNotFound(NotFound):
    def __init__(self, entry_id: PydanticObjectId) -> None:
        super().__init__(f"education {entry_id} not found")


class SkillNotFound(NotFound):
    def __init__(self, entry_id: PydanticObjectId) -> None:
        super().__init__(f"skill group {entry_id} not found")


class CertificationNotFound(NotFound):
    def __init__(self, entry_id: PydanticObjectId) -> None:
        super().__init__(f"certification {entry_id} not found")


# --- personal details --------------------------------------------------------


async def get_profile(user_id: PydanticObjectId) -> Profile:
    profile = await Profile.find_one({"userId": user_id})
    if profile is None:
        raise ProfileNotFound(f"no profile for user {user_id}")
    return profile


def _join(collection: str, alias: str) -> dict:
    return {
        "$lookup": {
            "from": collection,
            "localField": "_id",
            "foreignField": "userId",
            "as": alias,
        }
    }


def _with_id(row: dict) -> dict:
    """Aggregation returns raw documents, which are keyed by `_id`."""
    return {**row, "id": row["_id"]}


async def get_user_profile(user_id: PydanticObjectId) -> UserProfile:
    """Everything My Details shows, in one round trip.

    Starts at `accounts`, not `profile`: the profile row appears only once personal
    details are saved, and the four lists can be filled in before that.
    """
    pipeline = [
        {"$match": {"_id": user_id}},
        _join("profile", "profile"),
        {"$unwind": {"path": "$profile", "preserveNullAndEmptyArrays": True}},
        _join("work_experience", "work"),
        _join("education", "education"),
        _join("skills", "skill"),
        _join("certifications", "certification"),
    ]

    # Two awaits: the async driver's `aggregate` hands back the cursor itself.
    cursor = await Account.get_pymongo_collection().aggregate(pipeline)
    rows = await cursor.to_list(1)
    if not rows:
        raise UnknownUser(user_id)

    row = rows[0]
    profile = row.get("profile")
    return UserProfile(
        id=row["_id"],
        name=row["name"],
        email=row["email"],
        role=row.get("role", ""),
        profile_picture=row.get("profile_picture"),
        profile=ProfileRead(**_with_id(profile)) if profile else None,
        work=[ExperienceRead(**_with_id(entry)) for entry in row["work"]],
        education=[EducationRead(**_with_id(entry)) for entry in row["education"]],
        skill=[SkillRead(**_with_id(entry)) for entry in row["skill"]],
        certification=[CertificationRead(**_with_id(entry)) for entry in row["certification"]],
    )


async def create_profile(user_id: PydanticObjectId, payload: ProfileFields) -> Profile:
    # `userId` is `accounts._id` — the account module is what issues the login token,
    # so a profile hangs off the same identity the browser signed in as.
    if await Account.get(user_id) is None:
        raise UnknownUser(user_id)
    if await Profile.find_one({"userId": user_id}) is not None:
        raise ProfileExists("this user already has a profile")

    profile = Profile(userId=user_id, **payload.model_dump())
    await profile.insert()
    return profile


async def replace_profile(user_id: PydanticObjectId, payload: ProfileFields) -> Profile:
    profile = await get_profile(user_id)
    for field, value in payload.model_dump().items():
        setattr(profile, field, value)
    profile.updatedAt = datetime.now(UTC)
    await profile.save()
    return profile


# --- work experience ---------------------------------------------------------
# Every lookup below matches on `_id` and `userId` together, so one user's entry id
# cannot reach another user's row.


async def list_experience(user_id: PydanticObjectId) -> list[Experience]:
    return await Experience.find({"userId": user_id}).to_list()


async def add_experience(user_id: PydanticObjectId, payload: ExperienceFields) -> Experience:
    entry = Experience(userId=user_id, **payload.model_dump())
    await entry.insert()
    return entry


async def replace_experience(
    user_id: PydanticObjectId, entry_id: PydanticObjectId, payload: ExperienceFields
) -> Experience:
    entry = await Experience.find_one({"_id": entry_id, "userId": user_id})
    if entry is None:
        raise ExperienceNotFound(entry_id)

    for field, value in payload.model_dump().items():
        setattr(entry, field, value)
    entry.updatedAt = datetime.now(UTC)
    await entry.save()
    return entry


async def remove_experience(user_id: PydanticObjectId, entry_id: PydanticObjectId) -> None:
    entry = await Experience.find_one({"_id": entry_id, "userId": user_id})
    if entry is None:
        raise ExperienceNotFound(entry_id)
    await entry.delete()


# --- education ---------------------------------------------------------------


async def list_education(user_id: PydanticObjectId) -> list[Education]:
    return await Education.find({"userId": user_id}).to_list()


async def add_education(user_id: PydanticObjectId, payload: EducationFields) -> Education:
    entry = Education(userId=user_id, **payload.model_dump())
    await entry.insert()
    return entry


async def replace_education(
    user_id: PydanticObjectId, entry_id: PydanticObjectId, payload: EducationFields
) -> Education:
    entry = await Education.find_one({"_id": entry_id, "userId": user_id})
    if entry is None:
        raise EducationNotFound(entry_id)

    for field, value in payload.model_dump().items():
        setattr(entry, field, value)
    entry.updatedAt = datetime.now(UTC)
    await entry.save()
    return entry


async def remove_education(user_id: PydanticObjectId, entry_id: PydanticObjectId) -> None:
    entry = await Education.find_one({"_id": entry_id, "userId": user_id})
    if entry is None:
        raise EducationNotFound(entry_id)
    await entry.delete()


# --- skills ------------------------------------------------------------------


async def list_skills(user_id: PydanticObjectId) -> list[Skill]:
    return await Skill.find({"userId": user_id}).to_list()


async def add_skill(user_id: PydanticObjectId, payload: SkillFields) -> Skill:
    entry = Skill(userId=user_id, **payload.model_dump())
    await entry.insert()
    return entry


async def replace_skill(
    user_id: PydanticObjectId, entry_id: PydanticObjectId, payload: SkillFields
) -> Skill:
    entry = await Skill.find_one({"_id": entry_id, "userId": user_id})
    if entry is None:
        raise SkillNotFound(entry_id)

    for field, value in payload.model_dump().items():
        setattr(entry, field, value)
    entry.updatedAt = datetime.now(UTC)
    await entry.save()
    return entry


async def remove_skill(user_id: PydanticObjectId, entry_id: PydanticObjectId) -> None:
    entry = await Skill.find_one({"_id": entry_id, "userId": user_id})
    if entry is None:
        raise SkillNotFound(entry_id)
    await entry.delete()


# --- certifications ----------------------------------------------------------


async def list_certifications(user_id: PydanticObjectId) -> list[Certification]:
    return await Certification.find({"userId": user_id}).to_list()


async def add_certification(
    user_id: PydanticObjectId, payload: CertificationFields
) -> Certification:
    entry = Certification(userId=user_id, **payload.model_dump())
    await entry.insert()
    return entry


async def replace_certification(
    user_id: PydanticObjectId, entry_id: PydanticObjectId, payload: CertificationFields
) -> Certification:
    entry = await Certification.find_one({"_id": entry_id, "userId": user_id})
    if entry is None:
        raise CertificationNotFound(entry_id)

    for field, value in payload.model_dump().items():
        setattr(entry, field, value)
    entry.updatedAt = datetime.now(UTC)
    await entry.save()
    return entry


async def remove_certification(user_id: PydanticObjectId, entry_id: PydanticObjectId) -> None:
    entry = await Certification.find_one({"_id": entry_id, "userId": user_id})
    if entry is None:
        raise CertificationNotFound(entry_id)
    await entry.delete()


# --- everything at once ------------------------------------------------------


async def get_resume(user_id: PydanticObjectId) -> UserProfile:
    """The same read, for rendering — where personal details are not optional: the
    contact line and summary come from them."""
    user = await get_user_profile(user_id)
    if user.profile is None:
        raise ProfileNotFound(f"no profile for user {user_id}")
    return user
