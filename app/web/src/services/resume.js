import { axiosInstance, orNull } from "@/lib/axiosInstance";

/** GET /api/resume/{jobId} — the latest tailored .tex. Null before tailoring runs. */
export function getResume(jobId) {
    return orNull(axiosInstance.get(`/resume/${jobId}`));
}

/** GET /api/resume/{jobId}/versions — newest first. */
export function listResumeVersions(jobId) {
    return axiosInstance.get(`/resume/versions/${jobId}`);
}

/** GET /api/resume/base — the default resume. Null until one is submitted. */
export function getBaseResume() {
    return orNull(axiosInstance.get("/resume/base"));
}

/** PUT /api/resume/base — store the approved .tex verbatim. Replaces any earlier one. */
export function saveBaseResume({ templateId, tex }) {
    return axiosInstance.put("/resume/base", { templateId: templateId, tex });
}

/** GET /api/resume/base/pdf — the stored .tex compiled by pdflatex. */
export function getBaseResumePdf() {
    return axiosInstance.get("/resume/base/pdf", { responseType: "blob" });
}
