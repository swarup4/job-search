import { AI_URL, ApiError, aiInstance } from "@/lib/axiosInstance";
import { readToken } from "@/lib/session";

/**
 * Background runs on the AI tier, all shaped the same way under `/api/runs/{kind}`:
 *
 * - `discovery` — scrape the enabled career sources for new jobs
 * - `analysis` — details, embedding, tech stack and match for chosen or newest jobs
 * - `scoring` — a match score for every job you have none for yet
 *
 * `POST /start` starts one (or answers yours, while it is going); `GET /events` streams
 * your latest from `run_started`, which carries the run — or answers 204 when there is
 * none, which `followRun` resolves as `{ none: true }`.
 */

/** POST /api/runs/{kind}/start. Analysis takes `{ jobIds }` or `{ newest }`; the others no body. */
export function startRun(kind, body) {
    return aiInstance.post(`/runs/${kind}/start`, body);
}

/**
 * GET /api/runs/{kind}/events — the run's progress as server-sent events, closing after
 * `run_done`.
 *
 * `fetch`, not `EventSource`: EventSource cannot send the Authorization header, and
 * putting the token in the URL would write it into every access log. `lastEventId`
 * resumes after a dropped connection without replaying what was already shown.
 */
export async function followRun(kind, { onEvent, lastEventId = null, signal }) {
    const headers = { Accept: "text/event-stream", Authorization: `Bearer ${readToken()}` };
    if (lastEventId != null) headers["Last-Event-ID"] = String(lastEventId);

    let response;
    try {
        response = await fetch(`${AI_URL}/runs/${kind}/events`, { headers, signal });
    } catch (failure) {
        if (failure?.name === "AbortError") return;
        throw new ApiError(`Cannot reach the AI tier at ${AI_URL}. Is it running?`, { cause: failure });
    }
    // 204: you have no run of this kind yet — nothing to stream, and not an error.
    if (response.status === 204) return { none: true };
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
