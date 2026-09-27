"use client";

import { useCallback } from "react";
import { useSelector } from "react-redux";
import Link from "next/link";
import { AlertTriangle, ArrowRight, Briefcase, CheckCheck, FileCheck2, Send } from "lucide-react";
import { PageHeader } from "@/layout/PageHeader";
import { StatCard } from "@/component/StatCard";
import { PipelineColumn } from "@/component/PipelineColumn";
import { AnalysisProgress, AnalyzeNewJobs, useAnalysis } from "@/component/Analysis";
import { Panel } from "@/component/ui/panel";
import { buttonVariants } from "@/component/ui/button";
import { COLUMNS, usePipeline } from "@/hooks/usePipeline";
import { useRefreshShell } from "@/hooks/useShellCounts";
import { ROUTES } from "@/routes";
import { selectShell } from "@/store/shell/shellSlice";
import { cn } from "@/util/helper";

/**
 * The Pipeline board, on the API: counts per column, each column's newest jobs with
 * their match scores, and the review gate. A client page because the bearer token
 * lives in sessionStorage, which a server component cannot read.
 */
export default function Page() {
    const board = usePipeline();
    const refreshShell = useRefreshShell();
    // When an analysis finishes, reload so the analyzed jobs show their scores, and
    // the badges pick up the keyword choices it created.
    const { reload } = board;
    const analysis = useAnalysis(
        useCallback(async () => {
            await reload();
            await refreshShell();
        }, [reload, refreshShell])
    );
    const ready = board.status === "ready";
    const counts = ready ? board.counts : null;

    return (
        <>
            <PageHeader title="Pipeline" subtitle="Every job discovery found, and where each one stands.">
                {ready ? <AnalyzeNewJobs analysis={analysis} unscored={board.unscored} /> : null}
            </PageHeader>

            <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
                <StatCard icon={Briefcase} value={counts?.new ?? "—"} label="New" />
                <StatCard icon={CheckCheck} value={counts?.shortlisted ?? "—"} label="Reviewed" tone="muted" />
                <StatCard icon={FileCheck2} value={counts?.staged ?? "—"} label="Resumes tailored" tone="muted" />
                <StatCard icon={Send} value={counts?.applied ?? "—"} label="Applied" tone="muted" />
            </div>

            <AnalysisProgress analysis={analysis} />

            <ReviewGate />

            {board.status === "error" ? (
                <Panel className="mt-6 flex items-start gap-2 px-5 py-4 text-[13px] text-risk-ink">
                    <AlertTriangle className="mt-0.5 size-[14px] shrink-0" />
                    {board.error}
                </Panel>
            ) : null}

            {board.status === "loading" ? (
                <p className="mt-6 text-[13px] text-muted-foreground">Loading the pipeline…</p>
            ) : null}

            {ready ? (
                <div className="mt-6 grid gap-5 md:grid-cols-2 xl:grid-cols-5">
                    {COLUMNS.map((column) => {
                        const data = board.columns[column.key];
                        return (
                            <PipelineColumn
                                key={column.key}
                                label={column.label}
                                empty={column.empty}
                                count={data.count}
                                cards={data.cards}
                                loadingMore={data.loadingMore}
                                error={data.error}
                                onMore={() => board.loadMore(column.key, data.cards.length)}
                            />
                        );
                    })}
                </div>
            ) : null}
        </>
    );
}

/** The approval gate — the one coloured surface on the page. Hidden when nothing waits. */
function ReviewGate() {
    // The same numbers the header and sidebar show, loaded once by the shell.
    const pending = useSelector(selectShell);
    const total = pending.keywordSelections + pending.staged;
    if (!total) return null;

    const parts = [];
    if (pending.keywordSelections) {
        parts.push(`${pending.keywordSelections} keyword selection${pending.keywordSelections === 1 ? "" : "s"}`);
    }
    if (pending.staged) {
        parts.push(`${pending.staged} application${pending.staged === 1 ? "" : "s"} to submit`);
    }

    return (
        <Panel className="mt-5 overflow-hidden">
            <div className="flex flex-wrap items-center gap-x-5 gap-y-3 bg-attention px-5 py-4">
                <div className="grid size-11 shrink-0 place-items-center rounded-md bg-attention-solid text-white">
                    <span className="text-[18px] font-bold">{total}</span>
                </div>
                <div className="min-w-0">
                    <p className="text-[16px] font-semibold text-attention-ink">Pending your review</p>
                    <p className="mt-0.5 text-[13px] text-attention-muted">
                        {parts.join(" · ")}. Nothing moves forward without you.
                    </p>
                </div>
                <span className="grow" />
                {pending.staged ? (
                    <Link
                        href={ROUTES.applications}
                        className={cn(buttonVariants({ variant: "attentionQuiet", size: "sm" }))}
                    >
                        Review applications
                    </Link>
                ) : null}
                {pending.nextJobId ? (
                    <Link
                        href={ROUTES.keywords(pending.nextJobId, "board")}
                        className={cn(buttonVariants({ variant: "attention", size: "sm" }))}
                    >
                        Select keywords
                        <ArrowRight />
                    </Link>
                ) : null}
            </div>
        </Panel>
    );
}
