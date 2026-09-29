import { axiosInstance } from "@/lib/axiosInstance";

/**
 * GET /api/application/tracker — the Applications screen in one call: `staged` (waiting on
 * your submit) and `submitted` (most recent first), each row with its job's title, company
 * and location joined in.
 */
export function getTracker() {
    return axiosInstance.get("/application/tracker");
}

/** GET /api/application/board — the Pipeline in one read: column totals, the first
 * `limit` cards of every column with your match joined in, and the unscored total. */
export function getBoard(limit) {
    return axiosInstance.get("/application/board", { params: { limit } });
}

/** GET /api/application/board/{column} — the next cards of one column ("Show more"). */
export function getBoardColumn(column, { skip, limit }) {
    return axiosInstance.get(`/application/board/${column}`, { params: { skip, limit } });
}

/** GET /api/application/shortlist — your shortlisted jobs, newest first, each with its
 * listing and your match counts joined in. One request for the whole screen. */
export function getShortlist() {
    return axiosInstance.get("/application/shortlist");
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
