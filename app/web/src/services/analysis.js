import { AI_URL, ApiError, aiInstance } from "@/lib/axiosInstance";
import { readToken } from "@/lib/session";

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

/**
 * GET /api/analysis/run/events — the latest run's progress as server-sent events,
 * one per step as it starts and ends, closing after `run_done`.
 *
 * `fetch`, not `EventSource`: EventSource cannot send the Authorization header, and
 * putting the token in the URL would write it into every access log. `lastEventId`
 * resumes after a dropped connection without replaying what was already shown.
 */
export async function followAnalysis({ onEvent, lastEventId = null, signal }) {
    const headers = { Accept: "text/event-stream", Authorization: `Bearer ${readToken()}` };
    if (lastEventId != null) headers["Last-Event-ID"] = String(lastEventId);

    let response;
    try {
        response = await fetch(`${AI_URL}/analysis/run/events`, { headers, signal });
    } catch (failure) {
        if (failure?.name === "AbortError") return;
        throw new ApiError(`Cannot reach the AI tier at ${AI_URL}. Is it running?`, { cause: failure });
    }
    if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new ApiError(body.detail ?? `The AI tier returned ${response.status}.`, {
            status: response.status,
        });
    }

    const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
    let buffer = "";
    for (;;) {
        const { value, done } = await reader.read();
        if (done) return;
        buffer += value;
        let cut;
        while ((cut = buffer.indexOf("\n\n")) >= 0) {
            const block = buffer.slice(0, cut);
            buffer = buffer.slice(cut + 2);
            const fields = Object.fromEntries(
                block
                    .split("\n")
                    .filter((line) => !line.startsWith(":") && line.includes(": "))
                    .map((line) => [line.slice(0, line.indexOf(": ")), line.slice(line.indexOf(": ") + 2)])
            );
            if (fields.data) onEvent(JSON.parse(fields.data), Number(fields.id));
        }
    }
}
