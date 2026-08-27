import { axiosInstance, orNull } from "@/lib/axiosInstance";

/** GET /api/job — the Search, Shortlist and Pipeline screens. */
export function listJobs({ status, shortlisted, company, limit = 50, skip = 0 } = {}) {
    return axiosInstance.get("/job", { params: { status, shortlisted, company, limit, skip } });
}

/** GET /api/job/{id} — null when the job is gone, which a stale link makes normal. */
export function getJob(jobId) {
    return orNull(axiosInstance.get(`/job/${jobId}`));
}

/** PATCH /api/job/{id} — the shortlist toggle and pipeline moves. */
export function updateJob(jobId, changes) {
    return axiosInstance.patch(`/job/${jobId}`, changes);
}

export function setShortlisted(jobId, shortlisted) {
    return updateJob(jobId, { shortlisted });
}
