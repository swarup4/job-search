"use client";

import { AlertTriangle, Loader2, Sparkles } from "lucide-react";

import { ApiError, getAnalysisRun, startAnalysis } from "@/services";
import { usePolledRun } from "@/hooks/usePolledRun";
import { Panel } from "@/component/ui/panel";
import { Button } from "@/component/ui/button";
import { Tooltip } from "@/component/ui/tooltip";

/** How many unscored jobs one "Analyze new jobs" click takes. */
export const BATCH = 10;

const PER_JOB = "About a minute and ~$0.001 per job.";

/**
 * An Analyze run: starting one — a single job, or the newest few unscored — and polling
 * it until it ends, when `onFinished` reloads the page's data from the database.
 *
 * Nothing is asked on page load: analysis results live in the database and every
 * screen reads them from there. The run's status is polled only while a run this page
 * started is going, to know when to reload.
 */
export function useAnalysis(onFinished) {
    const poll = usePolledRun(getAnalysisRun, onFinished, { fetchOnMount: false });

    async function start(body) {
        poll.setError(null);
        try {
            poll.watch(await startAnalysis(body));
        } catch (failure) {
            poll.setError(failure instanceof ApiError ? failure.message : "Could not start the analysis.");
        }
    }

    return { ...poll, start };
}

/** The header button: analyze the newest jobs you have not scored yet. */
export function AnalyzeNewJobs({ analysis, unscored }) {
    const take = Math.min(BATCH, unscored);
    return (
        <Tooltip
            align="end"
            content={`Renders, embeds, reads experience / salary / work mode / job type, and scores the newest ${take || BATCH} jobs you have not scored yet. ${PER_JOB}`}
        >
            <Button
                size="sm"
                onClick={() => analysis.start({ newest: take })}
                disabled={analysis.running || !take}
            >
                {analysis.running ? <Loader2 className="animate-spin" /> : <Sparkles />}
                {analysis.running ? "Analyzing…" : take ? `Analyze ${take} new jobs` : "No new jobs"}
            </Button>
        </Tooltip>
    );
}

/** Progress of the current or last run, under the stat cards. */
export function AnalysisProgress({ analysis }) {
    const { run, running, error, watching, checkAgain } = analysis;
    if (!run && !error) return null;

    const done = run?.results.length ?? 0;
    const total = run?.jobIds.length ?? 0;
    const problems = run?.results.filter(hadProblem).length ?? 0;
    const scored = run?.results.filter((result) => result.score != null).length ?? 0;

    let line = null;
    if (run && running) line = `Analyzing ${done} of ${total} job${total === 1 ? "" : "s"}…`;
    else if (run?.status === "done")
        line = `Analyzed ${total} job${total === 1 ? "" : "s"} — ${scored} scored${problems ? `, ${problems} with problems` : ""}.`;
    else if (run?.status === "failed") line = `Analysis stopped after ${done} of ${total}: ${run.error}`;

    return (
        <Panel className="mt-5 flex flex-wrap items-center gap-x-3 gap-y-1 px-5 py-3 text-[13px]">
            {running ? <Loader2 className="size-[15px] animate-spin text-primary" /> : <Sparkles className="size-[15px] text-primary" />}
            {line ? <span>{line}</span> : null}
            {error ? (
                <span className="inline-flex items-center gap-1.5 text-risk-ink">
                    <AlertTriangle className="size-[13px]" />
                    {error}
                    {running && !watching ? (
                        <button type="button" className="underline" onClick={checkAgain}>
                            Check again
                        </button>
                    ) : null}
                </span>
            ) : null}
        </Panel>
    );
}

function hadProblem(result) {
    return Boolean(result.error) || Object.values(result.steps ?? {}).some((step) => !step.ok);
}
