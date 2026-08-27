import { axiosInstance, orNull } from "@/lib/axiosInstance";

/** GET /api/resume/{job_id} — the latest tailored .tex. Null before tailoring runs. */
export function getResume(jobId) {
    return orNull(axiosInstance.get(`/resume/${jobId}`));
}

/** GET /api/resume/{job_id}/versions — newest first. */
export function listResumeVersions(jobId) {
    return axiosInstance.get(`/resume/${jobId}/versions`);
}
