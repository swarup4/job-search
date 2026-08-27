import { axiosInstance, orNull } from "@/lib/axiosInstance";

/** GET /api/match/{job_id} — null before the matching agent has scored the job. */
export function getMatch(jobId) {
    return orNull(axiosInstance.get(`/match/${jobId}`));
}

/** GET /api/match/pending — feeds the "⚠ Pending your review" banner. */
export function getPendingCounts() {
    return axiosInstance.get("/match/pending");
}

/**
 * POST /api/match/{job_id}/selection — resolves the FR-7.3 keyword interrupt.
 *
 * `selectedKeys` must be keys the agent offered in `missing`; the server rejects
 * anything else with a 422. An empty array is a valid answer: it means the user
 * looked and chose nothing. There is deliberately no bulk variant.
 */
export function recordSelection(jobId, selectedKeys) {
    return axiosInstance.post(`/match/${jobId}/selection`, { selected_keys: selectedKeys, skip: false });
}

/** The user passing on a job without selecting anything. */
export function skipSelection(jobId) {
    return axiosInstance.post(`/match/${jobId}/selection`, { selected_keys: [], skip: true });
}
