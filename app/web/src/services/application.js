import { axiosInstance, orNull } from "@/lib/axiosInstance";

/** GET /api/application — omit `status` for the whole pipeline. */
export function listApplications(status) {
    return axiosInstance.get("/application", { params: { status } });
}

/** GET /api/application/for-job/{job_id} — null when nothing is staged yet. */
export function getApplicationForJob(jobId) {
    return orNull(axiosInstance.get(`/application/for-job/${jobId}`));
}

export function getApplication(applicationId) {
    return orNull(axiosInstance.get(`/application/${applicationId}`));
}

/**
 * PATCH /api/application/{id}/status.
 *
 * Moving to `applied` requires `confirmedByUser` — the server returns 409 without
 * it. That is the FR-5.3 gate: the user submitted the form themselves, and this
 * call only records that they did. Nothing here submits anything.
 */
export function setApplicationStatus(applicationId, status, { note, confirmedByUser = false } = {}) {
    return axiosInstance.patch(`/application/${applicationId}/status`, {
        status,
        note,
        confirmed_by_user: confirmedByUser,
    });
}
