from beanie import PydanticObjectId
from fastapi import APIRouter, status

from modules.account import CurrentUser
from modules.profile import service
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
)

# Every route works on the caller's own profile: `user_id` comes from the token, so
# there is no id in any URL here and no way to ask for somebody else's.
router = APIRouter(tags=["profile"])


# --- personal details --------------------------------------------------------


@router.post("/createProfile", response_model=ProfileRead, status_code=status.HTTP_201_CREATED)
async def create_profile(payload: ProfileFields, user_id: CurrentUser) -> Profile:
    return await service.create_profile(user_id, payload)


@router.get("/getProfile", response_model=ProfileRead)
async def get_profile(user_id: CurrentUser) -> Profile:
    return await service.get_profile(user_id)


@router.put("/updateProfile", response_model=ProfileRead)
async def replace_profile(payload: ProfileFields, user_id: CurrentUser) -> Profile:
    return await service.replace_profile(user_id, payload)


# --- work experience ---------------------------------------------------------


@router.get("/getExperience", response_model=list[ExperienceRead])
async def list_experience(user_id: CurrentUser) -> list[Experience]:
    return await service.list_experience(user_id)


@router.post("/addExperience", response_model=ExperienceRead, status_code=status.HTTP_201_CREATED)
async def add_experience(payload: ExperienceFields, user_id: CurrentUser) -> Experience:
    return await service.add_experience(user_id, payload)


@router.put("/updateExperience/{entry_id}", response_model=ExperienceRead)
async def replace_experience(
    entry_id: PydanticObjectId, payload: ExperienceFields, user_id: CurrentUser
) -> Experience:
    return await service.replace_experience(user_id, entry_id, payload)


@router.delete("/deleteExperience/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_experience(entry_id: PydanticObjectId, user_id: CurrentUser) -> None:
    await service.remove_experience(user_id, entry_id)


# --- education ---------------------------------------------------------------


@router.get("/getEducation", response_model=list[EducationRead])
async def list_education(user_id: CurrentUser) -> list[Education]:
    return await service.list_education(user_id)


@router.post("/addEducation", response_model=EducationRead, status_code=status.HTTP_201_CREATED)
async def add_education(payload: EducationFields, user_id: CurrentUser) -> Education:
    return await service.add_education(user_id, payload)


@router.put("/updateEducation/{entry_id}", response_model=EducationRead)
async def replace_education(
    entry_id: PydanticObjectId, payload: EducationFields, user_id: CurrentUser
) -> Education:
    return await service.replace_education(user_id, entry_id, payload)


@router.delete("/deleteEducation/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_education(entry_id: PydanticObjectId, user_id: CurrentUser) -> None:
    await service.remove_education(user_id, entry_id)


# --- skills ------------------------------------------------------------------


@router.get("/getSkills", response_model=list[SkillRead])
async def list_skills(user_id: CurrentUser) -> list[Skill]:
    return await service.list_skills(user_id)


@router.post("/addSkill", response_model=SkillRead, status_code=status.HTTP_201_CREATED)
async def add_skill(payload: SkillFields, user_id: CurrentUser) -> Skill:
    return await service.add_skill(user_id, payload)


@router.put("/updateSkill/{entry_id}", response_model=SkillRead)
async def replace_skill(
    entry_id: PydanticObjectId, payload: SkillFields, user_id: CurrentUser
) -> Skill:
    return await service.replace_skill(user_id, entry_id, payload)


@router.delete("/deleteSkill/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_skill(entry_id: PydanticObjectId, user_id: CurrentUser) -> None:
    await service.remove_skill(user_id, entry_id)


# --- certifications ----------------------------------------------------------


@router.get("/getCertifications", response_model=list[CertificationRead])
async def list_certifications(user_id: CurrentUser) -> list[Certification]:
    return await service.list_certifications(user_id)


@router.post(
    "/addCertification", response_model=CertificationRead, status_code=status.HTTP_201_CREATED
)
async def add_certification(payload: CertificationFields, user_id: CurrentUser) -> Certification:
    return await service.add_certification(user_id, payload)


@router.put("/updateCertification/{entry_id}", response_model=CertificationRead)
async def replace_certification(
    entry_id: PydanticObjectId, payload: CertificationFields, user_id: CurrentUser
) -> Certification:
    return await service.replace_certification(user_id, entry_id, payload)


@router.delete("/deleteCertification/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_certification(entry_id: PydanticObjectId, user_id: CurrentUser) -> None:
    await service.remove_certification(user_id, entry_id)
