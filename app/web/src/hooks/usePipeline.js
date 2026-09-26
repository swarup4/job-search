"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import {
    ApiError,
    getJob,
    getJobCounts,
    getMatchSummaries,
    getPendingCounts,
    getResume,
    listApplications,
    listJobs,
} from "@/services";

/** Cards loaded per column at a time; "Show more" fetches the next page. */
const PAGE = 5;

/**
 * Four columns are job statuses. Interview is an application status — a job stays
 * `applied` while its application moves on — so that column is read from
 * applications and each card's job looked up.
 */
export const COLUMNS = [
    { key: "new", label: "New", empty: "Run discovery from Settings to find jobs." },
    { key: "reviewed", label: "Reviewed", empty: "Jobs you have looked at land here." },
    { key: "tailored", label: "Tailored", empty: "Jobs with a tailored resume." },
    { key: "applied", label: "Applied", empty: "Jobs you have applied to." },
    { key: "interview", label: "Interview", empty: "Applications that reached an interview." },
];

const JOB_COLUMNS = ["new", "reviewed", "tailored", "applied"];

const SOURCE_LABEL = {
    career_page: "Career page",
    linkedin: "LinkedIn",
    indeed: "Indeed",
    naukri: "Naukri",
    serpapi: "Google",
};

/**
 * Everything the Pipeline screen shows, from the API: per-column counts, the first
 * cards of each column with their match scores, the pending-review banner and the
 * sidebar badges. Match scores for all the cards being added come from one request.
 */
export function usePipeline() {
    const [state, setState] = useState({ status: "loading" });
    // Interview applications are listed once; "Show more" pages through this copy.
    const interviews = useRef([]);
    const loading = useRef(false);

    const load = useCallback(async () => {
        try {
            const [counts, pending, staged, shortlisted, interviewApps, ...firstPages] = await Promise.all([
                getJobCounts(),
                getPendingCounts(),
                listApplications("staged"),
                listJobs({ shortlisted: true, limit: 200 }),
                listApplications("interview"),
                ...JOB_COLUMNS.map((status) => listJobs({ status, limit: PAGE })),
            ]);
            interviews.current = interviewApps;

            const columns = {};
            await Promise.all(
                JOB_COLUMNS.map(async (key, i) => {
                    columns[key] = { count: counts[key], cards: await cardsFor(key, firstPages[i]) };
                })
            );
            columns.interview = {
                count: interviewApps.length,
                cards: await interviewCards(interviewApps.slice(0, PAGE)),
            };

            setState({
                status: "ready",
                counts,
                pending: {
                    keywordSelections: pending.keywordSelections,
                    nextJobId: pending.nextJobId,
                    staged: staged.length,
                },
                shellCounts: {
                    pending: pending.keywordSelections + staged.length,
                    shortlisted: shortlisted.length,
                },
                columns,
            });
        } catch (failure) {
            setState({ status: "error", error: messageOf(failure, "Could not load the pipeline.") });
        }
    }, []);

    useEffect(() => {
        // A ref, not state: React's development double-mount fires the effect twice.
        if (loading.current) return;
        loading.current = true;
        load();
    }, [load]);

    /** The next page of one column, after the `shown` cards already on screen. */
    const loadMore = useCallback(async (key, shown) => {
        setState((current) => patchColumn(current, key, { loadingMore: true, error: null }));
        try {
            const more =
                key === "interview"
                    ? await interviewCards(interviews.current.slice(shown, shown + PAGE))
                    : await cardsFor(key, await listJobs({ status: key, limit: PAGE, skip: shown }));
            setState((current) =>
                patchColumn(current, key, {
                    loadingMore: false,
                    cards: [...current.columns[key].cards, ...more],
                })
            );
        } catch (failure) {
            setState((current) =>
                patchColumn(current, key, { loadingMore: false, error: messageOf(failure, "Could not load more.") })
            );
        }
    }, []);

    return { ...state, loadMore, reload: load };
}

/** Jobs as cards, with their match summaries and — in Tailored — the resume file. */
async function cardsFor(key, jobs) {
    const [summaries, resumes] = await Promise.all([
        getMatchSummaries(jobs.map((job) => job.id)),
        key === "tailored" ? Promise.all(jobs.map((job) => getResume(job.id))) : [],
    ]);
    const byJob = new Map(summaries.map((summary) => [summary.jobId, summary]));
    return jobs.map((job, i) => toCard(job, byJob.get(job.id), { file: fileName(resumes[i]) }));
}

/** Interview applications as cards: each one's job, and its latest activity. */
async function interviewCards(applications) {
    const jobs = await Promise.all(applications.map((application) => getJob(application.jobId)));
    const pairs = applications.map((application, i) => [application, jobs[i]]).filter(([, job]) => job);
    const summaries = await getMatchSummaries(pairs.map(([, job]) => job.id));
    const byJob = new Map(summaries.map((summary) => [summary.jobId, summary]));
    return pairs.map(([application, job]) =>
        toCard(job, byJob.get(job.id), {
            when: application.lastActivityNote || `Interview · ${ago(application.lastActivityAt ?? application.stagedAt)}`,
            strong: true,
        })
    );
}

/**
 * The shape JobCard reads. A card needing your keyword choice says so before any risk,
 * since that one blocks the job from moving on.
 */
function toCard(job, summary, { file = null, when = null, strong = false } = {}) {
    let flag = null;
    if (summary?.reviewState === "pending") flag = { kind: "attention", text: "Keywords await you" };
    else if (summary?.risk) flag = { kind: "risk", text: summary.risk };

    const meta = [job.location, when ?? ago(job.discoveredAt), when ? null : SOURCE_LABEL[job.source]]
        .filter(Boolean)
        .join(" · ");

    return {
        id: job.id,
        company: job.company,
        role: job.title,
        // 0 until the job has been compared with your resume; `scored` says which.
        match: summary?.score ?? 0,
        scored: Boolean(summary),
        meta,
        flag,
        file,
        strong,
    };
}

function patchColumn(state, key, changes) {
    if (state.status !== "ready") return state;
    return { ...state, columns: { ...state.columns, [key]: { ...state.columns[key], ...changes } } };
}

function fileName(resume) {
    return resume?.filePath ? resume.filePath.split("/").pop() : null;
}

function ago(timestamp) {
    if (!timestamp) return null;
    const minutes = Math.round((Date.now() - new Date(timestamp).getTime()) / 60000);
    if (minutes < 1) return "just now";
    if (minutes < 60) return `${minutes}m ago`;
    if (minutes < 60 * 24) return `${Math.round(minutes / 60)}h ago`;
    if (minutes < 60 * 24 * 7) return `${Math.round(minutes / (60 * 24))}d ago`;
    return new Date(timestamp).toLocaleDateString(undefined, { dateStyle: "medium" });
}

function messageOf(failure, fallback) {
    return failure instanceof ApiError ? failure.message : fallback;
}
