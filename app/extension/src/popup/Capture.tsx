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
                    ? "Capturing…"
                    : state.kind === "done"
                      ? "Capture again"
                      : "Capture this page"}
            </button>

            {state.kind === "done" ? (
                state.outcome.duplicate ? (
                    <p className="hint">Already captured — this page has not changed.</p>
                ) : (
                    <p className="hint">
                        Saved {Math.max(1, Math.round(state.outcome.characters / 1000))}k characters
                        and {state.outcome.links} links from {REGION_NAMES[state.outcome.region]}.
                    </p>
                )
            ) : null}

            {state.kind === "failed" ? <p className="error">{state.message}</p> : null}
        </div>
    );
}
