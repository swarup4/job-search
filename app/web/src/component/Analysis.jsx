"use client";

import { useEffect, useRef, useState } from "react";
import { AlertTriangle, Loader2, Sparkles } from "lucide-react";

import { ApiError, followAnalysis, startAnalysis } from "@/services";
import { Panel } from "@/component/ui/panel";
import { Button } from "@/component/ui/button";
import { Tooltip } from "@/component/ui/tooltip";
import { toast } from "@/component/ui/toast";

/** How many unscored jobs one "Analyze new jobs" click takes. */
export const BATCH = 10;

const PER_JOB = "About a minute and ~$0.001 per job.";

const STEPS = {
    details: { doing: "Reading experience, salary, work mode and job type", done: "Details" },
    embedding: { doing: "Embedding the job description", done: "Embedding" },
    techStack: { doing: "Reading the tech stack", done: "Tech stack" },
    match: { doing: "Matching the job against your resume", done: "Match" },
};

/**
 * An Analyze run: starting one — a single job, or the newest few unscored — and
 * following its server-sent events until it ends, when `onFinished` reloads the page's
 * data from the database.
 *
 * Nothing is asked on page load: results live in the database. A single job announces
 * every step as a toast; a batch announces each job, since ten jobs of four steps
 * would bury the screen.
 */
export function useAnalysis(onFinished) {
    const [run, setRun] = useState(null);
    const [error, setError] = useState(null);
    const [watching, setWatching] = useState(true);
    // Refs, not state: the stream's handlers outlive the render that created them.
    const single = useRef(false);
    const lastId = useRef(null);
    const ended = useRef(false);
    const stream = useRef(null);
    const finished = useRef(onFinished);
    finished.current = onFinished;

    useEffect(() => () => stream.current?.abort(), []);

    function apply(event) {
        switch (event.type) {
            case "job_started":
                if (single.current) toast.info(`Analyzing ${event.title}…`);
                break;
            case "step_started":
                if (single.current) toast.info(`${STEPS[event.step]?.doing ?? event.step}…`);
                break;
            case "step": {
                if (!single.current) break;
                const label = STEPS[event.step]?.done ?? event.step;
                if (event.ok) toast.success(`${label}: ${event.note}`);
                else toast.error(`${label} failed: ${event.note}`);
                break;
            }
            case "job_done":
                setRun((prev) => (prev ? { ...prev, results: [...prev.results, event] } : prev));
                if (event.error) toast.error(`${event.title || "Job"}: ${event.error}`);
                else if (event.score != null)
                    toast.success(
                        single.current
                            ? `Analysis finished — ${event.score}% match.`
                            : `${event.title}: ${event.score}% match.`
                    );
                else if (single.current) toast.info("Analysis finished.");
                break;
            case "run_done":
                ended.current = true;
                setRun((prev) => (prev ? { ...prev, status: event.status, error: event.error } : prev));
                if (event.status === "failed") toast.error(event.error ?? "The analysis stopped.");
                else if (!single.current) toast.success("Analysis run finished.");
                finished.current?.();
                break;
            default:
                break;
        }
    }

    async function follow() {
        stream.current?.abort();
        const controller = new AbortController();
        stream.current = controller;
        setWatching(true);
        try {
            await followAnalysis({
                onEvent: (event, id) => {
                    lastId.current = id;
                    apply(event);
                },
                lastEventId: lastId.current,
                signal: controller.signal,
            });
            // The stream closed without saying the run ended — the AI tier restarted.
            if (!ended.current && !controller.signal.aborted) {
                setError("Lost the analysis progress.");
                setWatching(false);
            }
        } catch (failure) {
            if (controller.signal.aborted) return;
            setError(failure instanceof ApiError ? failure.message : "Lost the analysis progress.");
            setWatching(false);
        }
    }

    async function start(body) {
        setError(null);
        lastId.current = null;
        ended.current = false;
        try {
            const started = await startAnalysis(body);
            single.current = started.jobIds.length === 1;
            setRun(started);
            follow();
        } catch (failure) {
            setError(failure instanceof ApiError ? failure.message : "Could not start the analysis.");
        }
    }

    function checkAgain() {
        setError(null);
        follow();
    }

    return { run, running: run?.status === "running", error, watching, checkAgain, start };
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
