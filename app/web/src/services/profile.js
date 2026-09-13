import { axiosInstance } from "@/lib/axiosInstance";

/**
 * The signed-in user's own profile. None of these take a user id: the server reads
 * it from the bearer token, so there is no id in any of these URLs.
 */

/**
 * Everything the My Details screen shows, in one request: the account, the personal
 * details and the four lists, joined by an aggregation on the server.
 *
 * `profile` in the response is null until personal details are saved for the first
 * time. The lists do not wait for it — each is keyed by the user on its own — so
 * they can be filled in first and still come back here.
 */
export function getProfile() {
    return axiosInstance.get("/profile/getProfile");
}

export function createProfile(profile) {
    return axiosInstance.post("/profile/createProfile", profile);
}

export function updateProfile(profile) {
    return axiosInstance.put("/profile/updateProfile", profile);
}

// work experience

export function getExperience() {
    return axiosInstance.get("/profile/getExperience");
}

export function addExperience(entry) {
    return axiosInstance.post("/profile/addExperience", entry);
}

export function updateExperience(entryId, entry) {
    return axiosInstance.put(`/profile/updateExperience/${entryId}`, entry);
}

export function deleteExperience(entryId) {
    return axiosInstance.delete(`/profile/deleteExperience/${entryId}`);
}

// education

export function getEducation() {
    return axiosInstance.get("/profile/getEducation");
}

export function addEducation(entry) {
    return axiosInstance.post("/profile/addEducation", entry);
}

export function updateEducation(entryId, entry) {
    return axiosInstance.put(`/profile/updateEducation/${entryId}`, entry);
}

export function deleteEducation(entryId) {
    return axiosInstance.delete(`/profile/deleteEducation/${entryId}`);
}

// skills — one entry per group

export function getSkills() {
    return axiosInstance.get("/profile/getSkills");
}

export function addSkill(group) {
    return axiosInstance.post("/profile/addSkill", group);
}

export function updateSkill(entryId, group) {
    return axiosInstance.put(`/profile/updateSkill/${entryId}`, group);
}

export function deleteSkill(entryId) {
    return axiosInstance.delete(`/profile/deleteSkill/${entryId}`);
}

// certifications

export function getCertifications() {
    return axiosInstance.get("/profile/getCertifications");
}

export function addCertification(entry) {
    return axiosInstance.post("/profile/addCertification", entry);
}

export function updateCertification(entryId, entry) {
    return axiosInstance.put(`/profile/updateCertification/${entryId}`, entry);
}

export function deleteCertification(entryId) {
    return axiosInstance.delete(`/profile/deleteCertification/${entryId}`);
}
