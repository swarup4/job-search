import { axiosInstance, orNull } from "@/lib/axiosInstance";

/** GET /api/job — the Search, Shortlist and Pipeline screens. */
export function listJobs({ status, shortlisted, company, limit = 50, skip = 0 } = {}) {
    return axiosInstance.get("/job", { params: { status, shortlisted, company, limit, skip } });
}

/** GET /api/job/counts — how many jobs sit in each pipeline column, zeros included. */
export function getJobCounts() {
    return axiosInstance.get("/job/counts");
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

/** PATCH /api/job/updateJob/{id} — the shortlist toggle and pipeline moves. */
export function updateJob(jobId, changes) {
    return axiosInstance.patch(`/job/updateJob/${jobId}`, changes);
}

export function setShortlisted(jobId, shortlisted) {
    return updateJob(jobId, { shortlisted });
}
