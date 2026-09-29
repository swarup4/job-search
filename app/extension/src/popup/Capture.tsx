import { useState } from "react";

import { askWorker, type CaptureOutcome } from "@/shared/messages";
import type { CaptureRegion } from "@/shared/types";

/** How confident the extraction was, in words. `body` is the one worth reading:
 * it means no rule matched and the capture carries the whole page. */
const REGION_NAMES: Record<CaptureRegion, string> = {
    main: "the main content",
    article: "the article",
    heuristic: "the largest text block",
    body: "the whole page — no main region found",
};

type State =
    | { kind: "idle" }
    | { kind: "busy" }
    | { kind: "done"; outcome: CaptureOutcome }
    | { kind: "failed"; message: string };

export function Capture({ tabId }: { tabId: number }) {
    // Its own state, not the popup's `run()`: capturing must not grey out the
    // fill button, and a failed capture is not a failed fill.
    const [state, setState] = useState<State>({ kind: "idle" });

    function capture() {
        setState({ kind: "busy" });
        void (async () => {
            try {
                setState({
                    kind: "done",
                    outcome: await askWorker<CaptureOutcome>({ type: "captureTab", tabId }),
                });
            } catch (cause) {
                setState({
                    kind: "failed",
                    message: cause instanceof Error ? cause.message : String(cause),
                });
            }
        })();
    }

    return (
        <div className="stack">
            <button type="button" onClick={capture} disabled={state.kind === "busy"}>
                {state.kind === "busy"
                    ? "Capturing and reading…"
                    : state.kind === "done"
                      ? "Capture again"
                      : "Capture this page"}
            </button>

            {state.kind === "done" ? <Result outcome={state.outcome} /> : null}

            {state.kind === "failed" ? <p className="error">{state.message}</p> : null}
        </div>
    );
}

/** Stored, then read: the job it became, why it is not one, or why reading failed. */
function Result({ outcome }: { outcome: CaptureOutcome }) {
    if (outcome.duplicate && !outcome.processed && !outcome.processError) {
        return <p className="hint">Already captured — this page has not changed.</p>;
    }

    const stored = `Saved ${Math.max(1, Math.round(outcome.characters / 1000))}k characters from ${REGION_NAMES[outcome.region]}.`;
    if (outcome.processError) {
        return (
            <>
                <p className="hint">{stored}</p>
                <p className="error">Could not read it into a job: {outcome.processError}</p>
            </>
        );
    }

    const job = outcome.processed;
    if (!job?.parsed) {
        return (
            <>
                <p className="hint">{stored}</p>
                <p className="error">Not a job posting — {job?.reason ?? "nothing to read"}.</p>
            </>
        );
    }
    return (
        <p className="hint">
            {job.duplicate ? "Already a job" : "Saved"}: <strong>{job.title}</strong> at {job.company} —{" "}
            {job.technologies} {job.technologies === 1 ? "technology" : "technologies"}. Analyze it on the
            dashboard for the match score.
        </p>
    );
}
