import { axiosInstance, orNull } from "@/lib/axiosInstance";

/** GET /api/application — one status, several (an array), or omit it for all. */
export function listApplications(status) {
    return axiosInstance.get("/application", {
        params: { status },
        // Repeated keys (status=a&status=b), which is what FastAPI reads as a list.
        paramsSerializer: { indexes: null },
    });
}

/**
 * GET /api/application/badges — every number the header and sidebar show, and the
 * Pipeline's review banner: keyword choices waiting (and the oldest one's job), staged
 * applications, shortlisted jobs. One call for all of them.
 */
export function getBadges() {
    return axiosInstance.get("/application/badges");
}

/**
 * GET /api/application/tracker — the Applications screen in one call: `staged` (waiting on
 * your submit) and `submitted` (most recent first), each row with its job's title, company
 * and location joined in.
 */
export function getTracker() {
    return axiosInstance.get("/application/tracker");
}

/** GET /api/application/counts — the Pipeline's column totals for you, zeros included. */
export function getBoardCounts() {
    return axiosInstance.get("/application/counts");
}

/** GET /api/application/unstarted — the New column: jobs you have no application for. */
export function listUnstartedJobs({ limit = 50, skip = 0 } = {}) {
    return axiosInstance.get("/application/unstarted", { params: { limit, skip } });
}

/** POST /api/application/shortlist/{jobId} — starts your application; a repeat is a no-op. */
export function shortlistJob(jobId) {
    return axiosInstance.post(`/application/shortlist/${jobId}`);
}

/**
 * DELETE /api/application/shortlist/{jobId} — deletes an untouched application (the job
 * goes back to New), withdraws one with a resume, and is refused (409) once submitted.
 */
export function unshortlistJob(jobId) {
    return axiosInstance.delete(`/application/shortlist/${jobId}`);
}

export function setShortlisted(jobId, shortlisted) {
    return shortlisted ? shortlistJob(jobId) : unshortlistJob(jobId);
}

/** GET /api/application/for-job/{jobId} — null until you shortlist or tailor for the job. */
export function getApplicationForJob(jobId) {
    return orNull(axiosInstance.get(`/application/for-job/${jobId}`));
}

export function getApplication(applicationId) {
    return orNull(axiosInstance.get(`/application/getApplication/${applicationId}`));
}

/**
 * PATCH /api/application/{id}/status.
 *
 * Moving to `applied` requires `confirmedByUser` — the server returns 409 without
 * it. That is the FR-5.3 gate: the user submitted the form themselves, and this
 * call only records that they did. Nothing here submits anything.
 */
export function setApplicationStatus(applicationId, status, { note, confirmedByUser = false } = {}) {
    return axiosInstance.patch(`/application/status/${applicationId}`, {
        status,
        note,
        confirmedByUser: confirmedByUser,
    });
}
