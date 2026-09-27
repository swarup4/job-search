import { axiosInstance, orNull } from "@/lib/axiosInstance";

/** GET /api/job — the shared catalogue, newest first. Nothing on a job is per-user. */
export function listJobs({ company, limit = 50, skip = 0 } = {}) {
    return axiosInstance.get("/job", { params: { company, limit, skip } });
}

/**
 * POST /api/job/search — the Search screen. Empty fields are dropped; `total` counts every
 * match and `jobs` is one page of them, newest first.
 */
export function searchJobs(filters, { limit = 20, skip = 0 } = {}) {
    const body = Object.fromEntries(
        Object.entries(filters).filter(([, value]) => value !== "" && value != null)
    );
    return axiosInstance.post("/job/search", { ...body, limit, skip });
}

/**
 * GET /api/job/getJobDetails/{id} — the job and its description in one read (a
 * `$lookup` on the server). `description` is null when none is stored; the whole
 * answer is null when the job is gone.
 */
export function getJobDetails(jobId) {
    return orNull(axiosInstance.get(`/job/getJobDetails/${jobId}`));
}

/** GET /api/job/getJob/{id} — null when the job is gone, which a stale link makes normal. */
export function getJob(jobId) {
    return orNull(axiosInstance.get(`/job/getJob/${jobId}`));
}

/** PATCH /api/job/updateJob/{id} — listing details only; where you stand is an application. */
export function updateJob(jobId, changes) {
    return axiosInstance.patch(`/job/updateJob/${jobId}`, changes);
}
