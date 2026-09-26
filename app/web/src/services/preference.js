import { axiosInstance } from "@/lib/axiosInstance";

/**
 * Search targets — what discovery looks for, one set per account. Run discovery reads
 * the saved copy when it starts, so what is on screen after Save is what gets searched.
 */

/** GET /api/preference — the saved targets, or the defaults if none were saved yet. */
export function getPreferences() {
    return axiosInstance.get("/preference");
}

/** PUT /api/preference — a full replace of the whole form. */
export function savePreferences(preferences) {
    return axiosInstance.put("/preference", preferences);
}
