import { useCallback, useEffect, useState } from "react";

import { Capture } from "@/popup/Capture";
import { Review } from "@/popup/Review";
import { SignIn } from "@/popup/SignIn";
import { askWorker, type FrameResult, type TabContext } from "@/shared/messages";

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
        if (tabId === null) return;
        void run(async () => {
            const outcome = await askWorker<FrameResult>({ type: "fillTab", tabId, applicationId });
            // The in-page panel opens itself whenever there is something to review,
            // and it is the better surface for it — it stays open while the user
            // works through the form. Keeping the same counts and buttons in the
            // popup as well is two of everything.
            if (outcome.filled.length > 0 || outcome.pending.length > 0) {
                window.close();
                return;
            }
            setResult(outcome);
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
                            <span className="muted">
                                Filling from your profile and answer bank.
                            </span>
                        )}
                    </div>

                    {context.staged.length > 0 ? (
                        <select
                            value={applicationId ?? ""}
                            onChange={(event) => {
                                setChosenId(event.target.value || null);
                                setResult(null);
                            }}
                        >
                            <option value="">Not tracking this one</option>
                            {context.staged.map(({ application, job: staged }) => (
                                <option key={application.id} value={application.id}>
                                    {staged ? `${staged.title} — ${staged.company.name}` : application.id}
                                </option>
                            ))}
                        </select>
                    ) : null}

                    {result?.blocked ? <p className="hint">{result.blocked}</p> : null}
                    {error ? <p className="error">{error}</p> : null}

                    {result && !result.blocked ? (
                        <Review
                            result={result}
                            busy={busy}
                            tracked={applicationId !== null}
                            onShowPanel={() =>
                                void run(async () => {
                                    if (tabId !== null) await askWorker({ type: "showPanel", tabId });
                                    window.close();
                                })
                            }
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
                        <button type="button" className="primary" onClick={fill} disabled={busy}>
                            {busy ? "Filling…" : "Fill this form"}
                        </button>
                    )}

                    {tabId !== null ? <Capture tabId={tabId} /> : null}
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
