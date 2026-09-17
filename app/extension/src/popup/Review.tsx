import { useState } from "react";

import type { FrameResult, UserAnswer } from "@/shared/messages";

/** FR-5.4 in the popup: what was filled, where each value came from, and the
 * questions that got no answer rather than a guessed one. */
export function Review({
    result,
    busy,
    onAnswer,
    onClear,
    onSubmitted,
}: {
    result: FrameResult;
    busy: boolean;
    onAnswer: (answers: UserAnswer[]) => void;
    onClear: () => void;
    onSubmitted: () => void;
}) {
    const [draft, setDraft] = useState<Record<string, string>>({});

    const answers: UserAnswer[] = result.pending
        .filter((question) => (draft[question.selector] ?? "").trim() !== "")
        .map((question) => ({
            selector: question.selector,
            question: question.question,
            value: draft[question.selector] ?? "",
        }));

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

            {result.filled.length > 0 ? (
                <details open>
                    <summary>Filled fields</summary>
                    <ul className="fills">
                        {result.filled.map((field, index) => (
                            <li key={`${index}-${field.selector}`}>
                                <span className="label">{field.label}</span>
                                <span className="value">{field.value}</span>
                                <span className="src">
                                    {field.source === "profile" ? "profile" : "answer bank"}
                                </span>
                            </li>
                        ))}
                    </ul>
                </details>
            ) : null}

            {result.pending.length > 0 ? (
                <details open>
                    <summary>Unanswered — your words, not ours</summary>
                    <ul className="pending">
                        {result.pending.map((question, index) => (
                            <li key={`${index}-${question.selector}`}>
                                <label>{question.question}</label>
                                {question.kind === "select" && question.options.length > 0 ? (
                                    <select
                                        value={draft[question.selector] ?? ""}
                                        onChange={(event) =>
                                            setDraft({ ...draft, [question.selector]: event.target.value })
                                        }
                                    >
                                        <option value="">Leave blank</option>
                                        {question.options.map((option) => (
                                            <option key={option} value={option}>
                                                {option}
                                            </option>
                                        ))}
                                    </select>
                                ) : question.kind === "textarea" ? (
                                    <textarea
                                        rows={3}
                                        value={draft[question.selector] ?? ""}
                                        onChange={(event) =>
                                            setDraft({ ...draft, [question.selector]: event.target.value })
                                        }
                                    />
                                ) : (
                                    <input
                                        value={draft[question.selector] ?? ""}
                                        onChange={(event) =>
                                            setDraft({ ...draft, [question.selector]: event.target.value })
                                        }
                                    />
                                )}
                            </li>
                        ))}
                    </ul>
                    <button
                        type="button"
                        className="primary"
                        disabled={busy || answers.length === 0}
                        onClick={() => onAnswer(answers)}
                    >
                        Fill {answers.length || ""} answer{answers.length === 1 ? "" : "s"}
                    </button>
                </details>
            ) : null}

            <p className="hint">
                Check every highlighted field, attach anything left, then submit the form yourself.
            </p>

            <div className="row">
                <button type="button" onClick={onClear} disabled={busy}>
                    Clear highlights
                </button>
                <button type="button" className="confirm" onClick={onSubmitted} disabled={busy}>
                    I submitted this
                </button>
            </div>
        </div>
    );
}
