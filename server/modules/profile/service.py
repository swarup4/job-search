from datetime import UTC, datetime

from beanie import PydanticObjectId

from config.errors import Conflict, NotFound
from modules.profile.models import (
    Certification,
    CertificationFields,
    Education,
    EducationFields,
    Experience,
    ExperienceFields,
    Profile,
    ProfileFields,
    Resume,
    Skill,
    SkillFields,
)
from modules.user import User


class ProfileNotFound(NotFound):
    """No profile for this account — the user has not filled in My details."""


class ProfileExists(Conflict):
    """One profile per account — it is created once, then edited."""


class UnknownUser(NotFound):
    def __init__(self, user_id: PydanticObjectId) -> None:
        super().__init__(f"user {user_id} not found")


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


async def create_profile(user_id: PydanticObjectId, payload: ProfileFields) -> Profile:
    if await User.get(user_id) is None:
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
    await get_profile(user_id)
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
    await get_profile(user_id)
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
    await get_profile(user_id)
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
    await get_profile(user_id)
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


async def get_resume(user_id: PydanticObjectId) -> Resume:
    """What a template renders from: the five collections for one user."""
    return Resume(
        profile=await get_profile(user_id),
        experience=await list_experience(user_id),
        education=await list_education(user_id),
        skills=await list_skills(user_id),
        certifications=await list_certifications(user_id),
    )
