import { useCallback, useEffect, useState } from "react";

import { Review } from "@/popup/Review";
import { SignIn } from "@/popup/SignIn";
import { askWorker, type FrameResult, type TabContext, type UserAnswer } from "@/shared/messages";

const PLATFORM_NAMES: Record<string, string> = {
    lever: "Lever",
    greenhouse: "Greenhouse",
    workday: "Workday",
    linkedin_easy_apply: "LinkedIn Easy Apply",
    other: "this page",
};

export function App() {
    const [tabId, setTabId] = useState<number | null>(null);
    const [context, setContext] = useState<TabContext | null>(null);
    const [chosenId, setChosenId] = useState<string | null>(null);
    const [result, setResult] = useState<FrameResult | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [busy, setBusy] = useState(false);

    const load = useCallback(async (id: number) => {
        setError(null);
        try {
            setContext(await askWorker<TabContext>({ type: "context", tabId: id }));
        } catch (cause) {
            setError(cause instanceof Error ? cause.message : String(cause));
        }
    }, []);

    useEffect(() => {
        void (async () => {
            const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
            if (tab?.id === undefined) return;
            setTabId(tab.id);
            await load(tab.id);
        })();
    }, [load]);

    const applicationId = chosenId ?? context?.application?.id ?? null;

    async function run<T>(work: () => Promise<T>): Promise<void> {
        setBusy(true);
        setError(null);
        try {
            await work();
        } catch (cause) {
            setError(cause instanceof Error ? cause.message : String(cause));
        } finally {
            setBusy(false);
        }
    }

    function fill() {
        if (tabId === null || !applicationId) return;
        void run(async () => {
            setResult(await askWorker<FrameResult>({ type: "fillTab", tabId, applicationId }));
        });
    }

    function answer(answers: UserAnswer[]) {
        if (tabId === null || !applicationId) return;
        void run(async () => {
            const outcome = await askWorker<FrameResult>({
                type: "answerTab",
                tabId,
                applicationId,
                answers,
            });
            // Drop the ones now answered; whatever stayed pending stays listed.
            const done = new Set(outcome.answered.map((entry) => entry.question));
            setResult((current) =>
                current
                    ? {
                          ...current,
                          filled: current.filled,
                          pending: current.pending.filter((question) => !done.has(question.question)),
                      }
                    : current,
            );
        });
    }

    if (!context) {
        return (
            <main>
                <Header />
                {error ? <p className="error">{error}</p> : <p className="muted">Loading…</p>}
            </main>
        );
    }

    if (!context.account) {
        return (
            <main>
                <Header />
                <SignIn onSignedIn={() => tabId !== null && void load(tabId)} />
            </main>
        );
    }

    const chosen = context.staged.find((entry) => entry.application.id === applicationId);
    const job = chosen?.job ?? context.job;

    return (
        <main>
            <Header
                account={context.account.name}
                onSignOut={() =>
                    void run(async () => {
                        await askWorker({ type: "signOut" });
                        setContext(null);
                        if (tabId !== null) await load(tabId);
                    })
                }
            />

            {!context.fillable ? (
                <p className="muted">Open a job application page to fill it.</p>
            ) : context.staged.length === 0 ? (
                <p className="muted">
                    Nothing staged yet. Tailor a resume for a job in the dashboard, and it shows up
                    here.
                </p>
            ) : (
                <div className="stack">
                    <div className="job">
                        <span className="tag plain">{PLATFORM_NAMES[context.platform]}</span>
                        {job ? (
                            <>
                                <strong>{job.title}</strong>
                                <span className="muted">
                                    {job.company.name} · {job.location}
                                </span>
                            </>
                        ) : (
                            <span className="muted">Pick the job you are applying to.</span>
                        )}
                    </div>

                    <select
                        value={applicationId ?? ""}
                        onChange={(event) => {
                            setChosenId(event.target.value || null);
                            setResult(null);
                        }}
                    >
                        <option value="">Choose a staged application…</option>
                        {context.staged.map(({ application, job: staged }) => (
                            <option key={application.id} value={application.id}>
                                {staged ? `${staged.title} — ${staged.company.name}` : application.id}
                            </option>
                        ))}
                    </select>

                    {result?.blocked ? <p className="hint">{result.blocked}</p> : null}
                    {error ? <p className="error">{error}</p> : null}

                    {result && !result.blocked ? (
                        <Review
                            result={result}
                            busy={busy}
                            onAnswer={answer}
                            onClear={() =>
                                void run(async () => {
                                    if (tabId !== null) {
                                        await askWorker({ type: "clearHighlights", tabId });
                                    }
                                    setResult(null);
                                })
                            }
                            onSubmitted={() =>
                                void run(async () => {
                                    if (!applicationId) return;
                                    await askWorker({ type: "confirmSubmitted", applicationId });
                                    setResult(null);
                                    if (tabId !== null) await load(tabId);
                                })
                            }
                        />
                    ) : (
                        <button
                            type="button"
                            className="primary"
                            onClick={fill}
                            disabled={busy || !applicationId}
                        >
                            {busy ? "Filling…" : "Fill this form"}
                        </button>
                    )}
                </div>
            )}
        </main>
    );
}

function Header({ account, onSignOut }: { account?: string; onSignOut?: () => void }) {
    return (
        <header>
            <div>
                <strong>JobPilot</strong>
                <span className="muted"> · fills, never submits</span>
            </div>
            {account && onSignOut ? (
                <button type="button" className="link" onClick={onSignOut}>
                    {account} · sign out
                </button>
            ) : null}
        </header>
    );
}
