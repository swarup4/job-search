import { axiosInstance, orNull } from "@/lib/axiosInstance";

/** GET /api/profile — null until the profile is created. */
export function getProfile() {
    return orNull(axiosInstance.get("/profile"));
}

/**
 * POST /api/profile — `email` is mandatory and is the profile's key. Returns 409
 * if one already exists; there is one profile by design (PRD §4).
 */
export function createProfile(profile) {
    return axiosInstance.post("/profile", profile);
}

/** PATCH /api/profile — partial. 404 before the profile exists. */
export function updateProfile(changes) {
    return axiosInstance.patch("/profile", changes);
}

export function getPreferences() {
    return orNull(axiosInstance.get("/profile/preferences"));
}

/** PUT /api/profile/preferences — the whole Settings screen, replaced wholesale. */
export function setPreferences(preferences) {
    return axiosInstance.put("/profile/preferences", preferences);
}
