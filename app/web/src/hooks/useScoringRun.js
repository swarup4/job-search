"use client";

import { useRun } from "@/hooks/useRun";
import { toast } from "@/component/ui/toast";

/** A job page reloads when this fires for its job. */
export const MATCH_SCORED = "jobpilot:match-scored";

/**
 * The scoring run behind the header's Refresh: a match score for every job you have none
 * for yet. `trigger` starts one, or — while yours is going — says how far it has got.
 * Mounted in the header, so it keeps following while pages change.
 */
export function useScoringRun(onFinished) {
    const scoring = useRun("scoring", {
        onEvent: (event, { replay }) => {
            if (event.type !== "job_done") return;
            window.dispatchEvent(new CustomEvent(MATCH_SCORED, { detail: { jobId: event.jobId } }));
            if (replay) return;
            if (event.error) toast.error(`${event.title || "A job"}: ${event.error}`);
            else toast.success(`${event.title}: ${event.score}% match (${event.scored} scored).`);
        },
        onFinished: ({ status, error, scored, failed }) => {
            if (status === "failed") toast.error(error ?? "Scoring stopped.");
            else if (!scored && !failed) toast.info("Every job already has a match score.");
            else toast.success(`Scoring finished — ${scored} scored${failed ? `, ${failed} failed` : ""}.`);
            onFinished?.();
        },
    });

    async function trigger() {
        if (scoring.running) {
            toast.info(`Scoring in progress — ${scoring.run.scored} scored so far.`);
            return;
        }
        const { run, error } = await scoring.start();
        if (!run) {
            toast.error(error);
            return;
        }
        if (run.scored + run.failed > 0) toast.info(`Scoring in progress — ${run.scored} scored so far.`);
        else toast.info("Scoring your unscored jobs against your resume…");
    }

    return { running: scoring.running, trigger };
}
