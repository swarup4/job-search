import type { FrameResult } from "@/shared/messages";

/**
 * The popup's half of FR-5.4: the counts and the actions. The questions
 * themselves live in the in-page panel, because answering them means looking at
 * the form, and a popup closes as soon as you do.
 */
export function Review({
    result,
    busy,
    tracked,
    onShowPanel,
    onClear,
    onSubmitted,
}: {
    result: FrameResult;
    busy: boolean;
    /** False when the page matches nothing staged, so there is no application to
     * move to APPLIED and nothing was recorded. */
    tracked: boolean;
    onShowPanel: () => void;
    onClear: () => void;
    onSubmitted: () => void;
}) {
    return (
        <div className="stack">
            <div className="counts">
                <span className="tag good">{result.filled.length} filled</span>
                {result.pending.length > 0 ? (
                    <span className="tag warn">{result.pending.length} need you</span>
                ) : null}
                <span className={`tag ${result.resumeAttached ? "good" : "plain"}`}>
                    {result.resumeAttached ? "resume attached" : "no resume"}
                </span>
            </div>

            {result.resumeHint ? <p className="hint">{result.resumeHint}</p> : null}

            {result.pending.length > 0 ? (
                <>
                    <p className="hint">
                        {result.pending.length} question
                        {result.pending.length === 1 ? "" : "s"} could not be answered from what is
                        stored. Answer them in the panel on the page — it stays open while you work.
                    </p>
                    <button type="button" className="primary" onClick={onShowPanel} disabled={busy}>
                        Show the panel
                    </button>
                </>
            ) : result.scanned > 0 && result.filled.length === 0 ? (
                <p className="hint">
                    Found {result.scanned} field{result.scanned === 1 ? "" : "s"}, all already
                    answered on the page.
                </p>
            ) : (
                <p className="hint">
                    Check every highlighted field, then submit the form yourself.
                </p>
            )}

            <div className="row">
                <button type="button" onClick={onClear} disabled={busy}>
                    Clear highlights
                </button>
                {tracked ? (
                    <button type="button" className="confirm" onClick={onSubmitted} disabled={busy}>
                        I submitted this
                    </button>
                ) : null}
            </div>

            {!tracked ? (
                <p className="hint">
                    This page matches nothing staged, so the fill was not recorded against an
                    application.
                </p>
            ) : null}
        </div>
    );
}
