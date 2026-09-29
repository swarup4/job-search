import { aiInstance } from "@/lib/axiosInstance";

// One model call and a few reads — usually seconds, but a slow hosted model can
// outlast the 15s default, and a timeout here would hide a resume that was stored.
const TAILOR_TIMEOUT_MS = 90000;

/** POST /api/tailoring/{jobId} — tailor the default resume to this job's selected
 * keywords and store it as a new version. 409 before a selection or a default resume. */
export function tailorResume(jobId) {
    return aiInstance.post(`/tailoring/${jobId}`, null, { timeout: TAILOR_TIMEOUT_MS });
}
