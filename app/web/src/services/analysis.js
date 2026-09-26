import { aiInstance } from "@/lib/axiosInstance";

/**
 * The Analyze buttons, on the AI tier. Each job gets its HTML rendered, its
 * experience / salary / work mode / job type read from the text, its description
 * embedded, and a match score — about a minute and ~$0.001 per job.
 */

/** POST /api/analysis/run — `{ jobIds }` for chosen jobs, or `{ newest }` for the
 * newest N in the New column. 409 while another analysis is running. */
export function startAnalysis(body) {
    return aiInstance.post("/analysis/run", body);
}

/** GET /api/analysis/run — the latest analysis run, or null. */
export function getAnalysisRun() {
    return aiInstance.get("/analysis/run");
}
