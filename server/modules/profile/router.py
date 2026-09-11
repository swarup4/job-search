from beanie import PydanticObjectId
from fastapi import APIRouter, status

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

router = APIRouter(tags=["profile"])


# --- personal details --------------------------------------------------------


@router.post(
    "/createProfile/{user_id}", response_model=ProfileRead, status_code=status.HTTP_201_CREATED
)
async def create_profile(user_id: PydanticObjectId, payload: ProfileFields) -> Profile:
    return await service.create_profile(user_id, payload)


@router.get("/getProfile/{user_id}", response_model=ProfileRead)
async def get_profile(user_id: PydanticObjectId) -> Profile:
    return await service.get_profile(user_id)


@router.put("/updateProfile/{user_id}", response_model=ProfileRead)
async def replace_profile(user_id: PydanticObjectId, payload: ProfileFields) -> Profile:
    return await service.replace_profile(user_id, payload)


# --- work experience ---------------------------------------------------------


@router.get("/getExperience/{user_id}", response_model=list[ExperienceRead])
async def list_experience(user_id: PydanticObjectId) -> list[Experience]:
    return await service.list_experience(user_id)


@router.post(
    "/addExperience/{user_id}", response_model=ExperienceRead, status_code=status.HTTP_201_CREATED
)
async def add_experience(user_id: PydanticObjectId, payload: ExperienceFields) -> Experience:
    return await service.add_experience(user_id, payload)


@router.put("/updateExperience/{user_id}/{entry_id}", response_model=ExperienceRead)
async def replace_experience(
    user_id: PydanticObjectId, entry_id: PydanticObjectId, payload: ExperienceFields
) -> Experience:
    return await service.replace_experience(user_id, entry_id, payload)


@router.delete("/deleteExperience/{user_id}/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_experience(user_id: PydanticObjectId, entry_id: PydanticObjectId) -> None:
    await service.remove_experience(user_id, entry_id)


# --- education ---------------------------------------------------------------


@router.get("/getEducation/{user_id}", response_model=list[EducationRead])
async def list_education(user_id: PydanticObjectId) -> list[Education]:
    return await service.list_education(user_id)


@router.post(
    "/addEducation/{user_id}", response_model=EducationRead, status_code=status.HTTP_201_CREATED
)
async def add_education(user_id: PydanticObjectId, payload: EducationFields) -> Education:
    return await service.add_education(user_id, payload)


@router.put("/updateEducation/{user_id}/{entry_id}", response_model=EducationRead)
async def replace_education(
    user_id: PydanticObjectId, entry_id: PydanticObjectId, payload: EducationFields
) -> Education:
    return await service.replace_education(user_id, entry_id, payload)


@router.delete("/deleteEducation/{user_id}/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_education(user_id: PydanticObjectId, entry_id: PydanticObjectId) -> None:
    await service.remove_education(user_id, entry_id)


# --- skills ------------------------------------------------------------------


@router.get("/getSkills/{user_id}", response_model=list[SkillRead])
async def list_skills(user_id: PydanticObjectId) -> list[Skill]:
    return await service.list_skills(user_id)


@router.post("/addSkill/{user_id}", response_model=SkillRead, status_code=status.HTTP_201_CREATED)
async def add_skill(user_id: PydanticObjectId, payload: SkillFields) -> Skill:
    return await service.add_skill(user_id, payload)


@router.put("/updateSkill/{user_id}/{entry_id}", response_model=SkillRead)
async def replace_skill(
    user_id: PydanticObjectId, entry_id: PydanticObjectId, payload: SkillFields
) -> Skill:
    return await service.replace_skill(user_id, entry_id, payload)


@router.delete("/deleteSkill/{user_id}/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_skill(user_id: PydanticObjectId, entry_id: PydanticObjectId) -> None:
    await service.remove_skill(user_id, entry_id)


# --- certifications ----------------------------------------------------------


@router.get("/getCertifications/{user_id}", response_model=list[CertificationRead])
async def list_certifications(user_id: PydanticObjectId) -> list[Certification]:
    return await service.list_certifications(user_id)


@router.post(
    "/addCertification/{user_id}",
    response_model=CertificationRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_certification(
    user_id: PydanticObjectId, payload: CertificationFields
) -> Certification:
    return await service.add_certification(user_id, payload)


@router.put("/updateCertification/{user_id}/{entry_id}", response_model=CertificationRead)
async def replace_certification(
    user_id: PydanticObjectId, entry_id: PydanticObjectId, payload: CertificationFields
) -> Certification:
    return await service.replace_certification(user_id, entry_id, payload)


@router.delete("/deleteCertification/{user_id}/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_certification(user_id: PydanticObjectId, entry_id: PydanticObjectId) -> None:
    await service.remove_certification(user_id, entry_id)
