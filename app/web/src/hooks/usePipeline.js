"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError, getBoard, getBoardColumn } from "@/services";

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

const SOURCE_LABEL = {
    career_page: "Career page",
    linkedin: "LinkedIn",
    indeed: "Indeed",
    naukri: "Naukri",
    serpapi: "Google",
};

/**
 * The Pipeline's cards, in one request: the first few of each column with your match
 * joined in, each column with its own total for "Show more". The stat cards, the
 * Analyze button's count and the review banner read the status store instead.
 */
export function usePipeline() {
    const [state, setState] = useState({ status: "loading" });
    const loading = useRef(false);

    const load = useCallback(async () => {
        try {
            const board = await getBoard(PAGE);
            const columns = Object.fromEntries(
                Object.entries(board.columns).map(([key, column]) => [
                    key,
                    { count: column.count, cards: column.cards.map((card) => toCard(key, card)) },
                ])
            );
            setState({ status: "ready", columns });
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
            const more = (await getBoardColumn(key, { skip: shown, limit: PAGE })).map((card) =>
                toCard(key, card)
            );
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

/**
 * The shape JobCard reads, from one board card. A card needing your keyword choice says
 * so before any risk, since that one blocks the job from moving on.
 */
function toCard(key, card) {
    let flag = null;
    if (card.reviewState === "pending") flag = { kind: "attention", text: "Keywords await you" };
    else if (card.risk) flag = { kind: "risk", text: card.risk };

    const when =
        key === "interview"
            ? card.lastActivityNote || `Interview · ${ago(card.lastActivityAt ?? card.stagedAt)}`
            : null;
    const meta = [card.location, when ?? ago(card.discoveredAt), when ? null : SOURCE_LABEL[card.source]]
        .filter(Boolean)
        .join(" · ");

    return {
        id: card.id,
        company: card.company,
        role: card.title,
        // 0 until the job has been compared with your resume; `scored` says which.
        match: card.score ?? 0,
        scored: card.score != null,
        meta,
        flag,
        file: key === "staged" ? fileName(card.texPath) : null,
        strong: key === "interview",
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
