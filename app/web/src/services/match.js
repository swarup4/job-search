import { axiosInstance, orNull } from "@/lib/axiosInstance";

/** GET /api/match/getMatch/{jobId} — null before the matching agent has scored the job. */
export function getMatch(jobId) {
    return orNull(axiosInstance.get(`/match/getMatch/${jobId}`));
}

/**
 * GET /api/match/summaries — score, review state and first risk for many jobs in one
 * call. A job with no match is absent from the answer, not an error.
 */
export function getMatchSummaries(jobIds) {
    if (!jobIds.length) return Promise.resolve([]);
    // Repeated keys (jobIds=a&jobIds=b), which is what FastAPI reads as a list.
    return axiosInstance.get("/match/summaries", {
        params: { jobIds },
        paramsSerializer: { indexes: null },
    });
}

/** GET /api/match/unscored — `total` jobs you have not scored yet, and the newest `limit`. */
export function getUnscoredJobs(limit = 0) {
    return axiosInstance.get("/match/unscored", { params: { limit } });
}

/** GET /api/match/pending — feeds the "⚠ Pending your review" banner, and names the
 * longest-waiting job (`nextJobId`) for its Select keywords link. */
export function getPendingCounts() {
    return axiosInstance.get("/match/pending");
}

/**
 * POST /api/match/{jobId}/selection — resolves the FR-7.3 keyword interrupt.
 *
 * `selectedKeys` must be keys the agent offered in `missing`; the server rejects
 * anything else with a 422. An empty array is a valid answer: it means the user
 * looked and chose nothing. There is deliberately no bulk variant.
 */
export function recordSelection(jobId, selectedKeys) {
    return axiosInstance.post(`/match/selection/${jobId}`, { selectedKeys: selectedKeys, skip: false });
}

/** The user passing on a job without selecting anything. */
export function skipSelection(jobId) {
    return axiosInstance.post(`/match/selection/${jobId}`, { selectedKeys: [], skip: true });
}
