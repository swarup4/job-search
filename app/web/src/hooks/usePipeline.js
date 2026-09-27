"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import {
    ApiError,
    getBoardCounts,
    getJob,
    getMatchSummaries,
    getUnscoredJobs,
    listApplications,
    listUnstartedJobs,
} from "@/services";

/** Cards loaded per column at a time; "Show more" fetches the next page. */
const PAGE = 5;

/**
 * New is every job you have no application for. The other columns are your
 * applications by status — shortlisting is what moves a job out of New. Column keys
 * are the count keys `GET /application/counts` answers with.
 */
export const COLUMNS = [
    { key: "new", label: "New", empty: "Run discovery from Settings to find jobs." },
    { key: "shortlisted", label: "Reviewed", empty: "Jobs you shortlist land here." },
    { key: "staged", label: "Tailored", empty: "Jobs with a tailored resume." },
    { key: "applied", label: "Applied", empty: "Jobs you have applied to." },
    { key: "interview", label: "Interview", empty: "Applications that reached an interview." },
];

const APPLICATION_STATUSES = {
    shortlisted: ["shortlisted"],
    staged: ["staged"],
    applied: ["applied", "viewed"],
    interview: ["interview"],
};

const SOURCE_LABEL = {
    career_page: "Career page",
    linkedin: "LinkedIn",
    indeed: "Indeed",
    naukri: "Naukri",
    serpapi: "Google",
};

/**
 * Everything the Pipeline screen shows, from the API: per-column counts, the first
 * cards of each column with their match scores, and how many jobs are still unscored
 * for the Analyze button. The review banner reads the shell's badges instead.
 */
export function usePipeline() {
    const [state, setState] = useState({ status: "loading" });
    // Each application column is listed once; "Show more" pages through this copy.
    const applications = useRef({});
    const loading = useRef(false);

    const load = useCallback(async () => {
        try {
            const keys = Object.keys(APPLICATION_STATUSES);
            const [counts, unscored, firstNew, ...lists] = await Promise.all([
                getBoardCounts(),
                getUnscoredJobs(0),
                listUnstartedJobs({ limit: PAGE }),
                ...keys.map((key) => listApplications(APPLICATION_STATUSES[key])),
            ]);
            applications.current = Object.fromEntries(keys.map((key, i) => [key, lists[i]]));

            const columns = { new: { count: counts.new, cards: await jobCards(firstNew) } };
            await Promise.all(
                keys.map(async (key) => {
                    columns[key] = {
                        count: applications.current[key].length,
                        cards: await applicationCards(key, applications.current[key].slice(0, PAGE)),
                    };
                })
            );

            setState({
                status: "ready",
                counts,
                unscored: unscored.total,
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
                key === "new"
                    ? await jobCards(await listUnstartedJobs({ limit: PAGE, skip: shown }))
                    : await applicationCards(key, applications.current[key].slice(shown, shown + PAGE));
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

async function summariesFor(jobs) {
    const summaries = await getMatchSummaries(jobs.map((job) => job.id));
    return new Map(summaries.map((summary) => [summary.jobId, summary]));
}

async function jobCards(jobs) {
    const byJob = await summariesFor(jobs);
    return jobs.map((job) => toCard(job, byJob.get(job.id)));
}

/** Applications as cards: each one's job, and what the column needs to say about it. */
async function applicationCards(key, rows) {
    const jobs = await Promise.all(rows.map((application) => getJob(application.jobId)));
    const pairs = rows.map((application, i) => [application, jobs[i]]).filter(([, job]) => job);
    const byJob = await summariesFor(pairs.map(([, job]) => job));
    return pairs.map(([application, job]) =>
        toCard(job, byJob.get(job.id), {
            file: key === "staged" ? fileName(application.texPath) : null,
            when:
                key === "interview"
                    ? application.lastActivityNote ||
                      `Interview · ${ago(application.lastActivityAt ?? application.stagedAt)}`
                    : null,
            strong: key === "interview",
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

function fileName(path) {
    return path ? path.split("/").pop() : null;
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
