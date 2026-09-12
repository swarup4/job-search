import { axiosInstance, orNull } from "@/lib/axiosInstance";

/** Personal details. GET is null until the profile is created. */
export function getProfile(userId) {
    return orNull(axiosInstance.get(`/profile/getProfile/${userId}`));
}

export function createProfile(userId, profile) {
    return axiosInstance.post(`/profile/createProfile/${userId}`, profile);
}

export function updateProfile(userId, profile) {
    return axiosInstance.put(`/profile/updateProfile/${userId}`, profile);
}

// work experience

export function getExperience(userId) {
    return axiosInstance.get(`/profile/getExperience/${userId}`);
}

export function addExperience(userId, entry) {
    return axiosInstance.post(`/profile/addExperience/${userId}`, entry);
}

export function updateExperience(userId, entryId, entry) {
    return axiosInstance.put(`/profile/updateExperience/${userId}/${entryId}`, entry);
}

export function deleteExperience(userId, entryId) {
    return axiosInstance.delete(`/profile/deleteExperience/${userId}/${entryId}`);
}

// education

export function getEducation(userId) {
    return axiosInstance.get(`/profile/getEducation/${userId}`);
}

export function addEducation(userId, entry) {
    return axiosInstance.post(`/profile/addEducation/${userId}`, entry);
}

export function updateEducation(userId, entryId, entry) {
    return axiosInstance.put(`/profile/updateEducation/${userId}/${entryId}`, entry);
}

export function deleteEducation(userId, entryId) {
    return axiosInstance.delete(`/profile/deleteEducation/${userId}/${entryId}`);
}

// skills — one entry per group

export function getSkills(userId) {
    return axiosInstance.get(`/profile/getSkills/${userId}`);
}

export function addSkill(userId, group) {
    return axiosInstance.post(`/profile/addSkill/${userId}`, group);
}

export function updateSkill(userId, entryId, group) {
    return axiosInstance.put(`/profile/updateSkill/${userId}/${entryId}`, group);
}

export function deleteSkill(userId, entryId) {
    return axiosInstance.delete(`/profile/deleteSkill/${userId}/${entryId}`);
}

// certifications

export function getCertifications(userId) {
    return axiosInstance.get(`/profile/getCertifications/${userId}`);
}

export function addCertification(userId, entry) {
    return axiosInstance.post(`/profile/addCertification/${userId}`, entry);
}

export function updateCertification(userId, entryId, entry) {
    return axiosInstance.put(`/profile/updateCertification/${userId}/${entryId}`, entry);
}

export function deleteCertification(userId, entryId) {
    return axiosInstance.delete(`/profile/deleteCertification/${userId}/${entryId}`);
}
