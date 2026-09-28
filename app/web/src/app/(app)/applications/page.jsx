"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { AlertTriangle, ArrowRight, Bookmark, CheckCheck, ExternalLink, Lock, Send } from "lucide-react";
import { PageHeader } from "@/layout/PageHeader";
import { StatCard } from "@/component/StatCard";
import { StatusChip } from "@/component/StatusChip";
import { FilePath } from "@/component/FilePath";
import { ShortlistButton } from "@/component/ShortlistButton";
import { Panel, PanelBody, PanelHeader, PanelTitle } from "@/component/ui/panel";
import { buttonVariants } from "@/component/ui/button";
import { Tooltip } from "@/component/ui/tooltip";
import { ApiError, getTracker, unshortlistJob } from "@/services";
import { useRefreshShell } from "@/hooks/useShellCounts";
import { ROUTES } from "@/routes";
import { cn } from "@/util/helper";

const ATS = {
    workday: "Workday",
    greenhouse: "Greenhouse",
    lever: "Lever",
    linkedin_easy_apply: "LinkedIn Easy Apply",
};

const STATUS = {
    applied: "Applied",
    viewed: "Viewed",
    interview: "Interview",
    offer: "Offer",
    rejected: "Rejected",
    withdrawn: "Withdrawn",
};

// Closed: no follow-up is due, and the row is dimmed.
const CLOSED = new Set(["rejected", "withdrawn"]);

/**
 * Every application in the order it moves — shortlisted (being prepared), staged
 * (waiting on your submit), submitted — from one call. JobPilot fills forms and stops;
 * the extension moves a row to Submitted only when you confirm you pressed Submit.
 */
export default function Page() {
    const [data, setData] = useState({ status: "loading", shortlisted: [], staged: [], submitted: [] });
    const fetching = useRef(false);
    const refreshShell = useRefreshShell();

    const load = useCallback(async () => {
        try {
            const { shortlisted, staged, submitted } = await getTracker();
            setData({ status: "ready", shortlisted, staged, submitted });
        } catch (failure) {
            setData({
                status: "error",
                shortlisted: [],
                staged: [],
                submitted: [],
                error: failure instanceof ApiError ? failure.message : "Could not load your applications.",
            });
        }
    }, []);

    useEffect(() => {
        // A ref, not state: React's development double-mount fires the effect twice.
        if (fetching.current) return;
        fetching.current = true;
        load();
    }, [load]);

    // A removed bookmark takes the row with it; the row was nothing but the shortlist.
    async function unshortlist(row) {
        await unshortlistJob(row.jobId);
        setData((current) => ({
            ...current,
            shortlisted: current.shortlisted.filter((other) => other.id !== row.id),
        }));
        refreshShell();
    }

    const { shortlisted, staged, submitted } = data;
    const ready = data.status === "ready";
    const active = submitted.filter((row) => !CLOSED.has(row.status)).length;
    const interviews = submitted.filter((row) => row.status === "interview").length;

    return (
        <>
            <PageHeader
                title="Applications"
                subtitle={
                    staged.length
                        ? `${staged.length} staged and waiting on you. JobPilot fills forms and stops — you submit.`
                        : "JobPilot fills forms and stops — you submit."
                }
            />

            <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
                <StatCard icon={Bookmark} value={ready ? shortlisted.length : "—"} label="Shortlisted" tone="muted" />
                <StatCard icon={Lock} value={ready ? staged.length : "—"} label="Staged for you" tone="attention" />
                <StatCard icon={Send} value={ready ? active : "—"} label="Active applications" />
                <StatCard icon={CheckCheck} value={ready ? interviews : "—"} label="In interview" tone="muted" />
            </div>

            {data.status === "error" ? (
                <Panel className="mt-5 flex items-start gap-2 px-5 py-4 text-[13px] text-risk-ink">
                    <AlertTriangle className="mt-0.5 size-[14px] shrink-0" />
                    {data.error}
                </Panel>
            ) : null}

            {data.status === "loading" ? (
                <p className="mt-5 text-[13px] text-muted-foreground">Loading your applications…</p>
            ) : null}

            {ready ? (
                <>
                    {/* SHORTLISTED */}
                    <Panel className="mt-5 overflow-hidden">
                        <PanelHeader>
                            <PanelTitle>Shortlisted — being prepared</PanelTitle>
                            <span className="text-[13px] text-muted-foreground">{shortlisted.length}</span>
                            <span className="grow" />
                            <span className="text-[12.5px] text-muted-foreground">
                                Choose keywords on a job to tailor its resume and stage it.
                            </span>
                        </PanelHeader>

                        {shortlisted.length ? (
                            shortlisted.map((row, i) => (
                                <div
                                    key={row.id}
                                    className={cn(
                                        "flex flex-wrap items-center gap-x-6 gap-y-3 px-5 py-4",
                                        i < shortlisted.length - 1 && "border-b border-border"
                                    )}
                                >
                                    <div className="min-w-[240px] grow basis-0">
                                        <Link
                                            href={ROUTES.job(row.jobId, "applications")}
                                            className="text-[14.5px] font-medium hover:text-primary"
                                        >
                                            {row.title}
                                        </Link>
                                        <p className="mt-0.5 text-[12.5px] text-muted-foreground">
                                            {row.company} · {row.location}
                                        </p>
                                    </div>
                                    <span className="text-[12.5px] text-muted-foreground">
                                        Shortlisted {ago(row.shortlistedAt)}
                                    </span>
                                    <ShortlistButton shortlisted size="sm" onToggle={() => unshortlist(row)} />
                                    <Link
                                        href={ROUTES.job(row.jobId, "applications")}
                                        className={buttonVariants({ variant: "outline", size: "sm" })}
                                    >
                                        Prepare
                                        <ArrowRight />
                                    </Link>
                                </div>
                            ))
                        ) : (
                            <PanelBody className="py-6 text-[13.5px] text-muted-foreground">
                                Nothing shortlisted. Bookmark a job on Search or on its page and it shows up here.
                            </PanelBody>
                        )}
                    </Panel>

                    {/* STAGED */}
                    <Panel className="mt-5 overflow-hidden">
                        <div className="flex flex-wrap items-center gap-3 bg-attention px-5 py-3.5">
                            <Lock className="size-[15px] shrink-0 text-attention-ink" />
                            <h2 className="text-[14px] font-medium text-attention-ink">
                                Staged — you submit this yourself
                            </h2>
                            <span className="text-[12.5px] text-attention-muted">
                                The extension fills the form and highlights every field. It never clicks Submit.
                            </span>
                        </div>

                        {staged.length ? (
                            staged.map((row, i) => (
                                <PanelBody
                                    key={row.id}
                                    className={cn(
                                        "flex flex-wrap items-center gap-x-8 gap-y-5 py-5",
                                        i < staged.length - 1 && "border-b border-border"
                                    )}
                                >
                                    <div className="min-w-[240px]">
                                        <Link
                                            href={ROUTES.job(row.jobId, "applications")}
                                            className="text-[16px] font-medium hover:text-primary"
                                        >
                                            {row.title}
                                        </Link>
                                        <p className="mt-1 text-[13px] text-muted-foreground">
                                            {[row.company, row.location, ATS[row.ats]].filter(Boolean).join(" · ")}
                                        </p>
                                    </div>

                                    <div className="flex items-center gap-7">
                                        <Tally n={row.fieldsFilled} label="fields matched" />
                                        <Tally n={row.needsAnswer} label="need you" tone="attention" />
                                    </div>

                                    {row.texPath ? (
                                        <div className="min-w-[280px]">
                                            <p className="mb-2 text-[12px] text-muted-foreground">attach by hand</p>
                                            <FilePath path={row.texPath} />
                                        </div>
                                    ) : null}

                                    <span className="grow" />
                                    <OpenAndAutofill url={row.applyUrl ?? row.listingUrl} />
                                </PanelBody>
                            ))
                        ) : (
                            <PanelBody className="py-6 text-[13.5px] text-muted-foreground">
                                Nothing staged. A job is staged here once its resume is tailored.
                            </PanelBody>
                        )}
                    </Panel>

                    {/* SUBMITTED */}
                    <Panel className="mt-5 overflow-hidden">
                        <PanelHeader>
                            <PanelTitle>Submitted</PanelTitle>
                            <span className="text-[13px] text-muted-foreground">{submitted.length}</span>
                        </PanelHeader>

                        {submitted.length ? (
                            <div className="overflow-x-auto">
                                <table className="w-full min-w-[860px] text-left">
                                    <thead>
                                        <tr className="border-b border-border bg-well">
                                            {["Role", "Status", "Resume sent", "Last activity", "Follow-up"].map((h) => (
                                                <th
                                                    key={h}
                                                    className="px-5 py-3 text-[12px] font-medium uppercase tracking-wide text-muted-foreground"
                                                >
                                                    {h}
                                                </th>
                                            ))}
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {submitted.map((row, i) => (
                                            <tr
                                                key={row.id}
                                                className={cn(
                                                    "transition-colors hover:bg-secondary/50",
                                                    i < submitted.length - 1 && "border-b border-border",
                                                    CLOSED.has(row.status) && "opacity-55"
                                                )}
                                            >
                                                <td className="px-5 py-4">
                                                    <Link
                                                        href={ROUTES.job(row.jobId, "applications")}
                                                        className="text-[14px] font-medium hover:text-primary"
                                                    >
                                                        {row.title}
                                                    </Link>
                                                    <p className="mt-0.5 text-[12.5px] text-muted-foreground">{row.company}</p>
                                                </td>
                                                <td className="px-5 py-4">
                                                    <StatusChip status={STATUS[row.status] ?? row.status} />
                                                </td>
                                                <td className="px-5 py-4 font-mono text-[12px] text-muted-foreground">
                                                    {fileName(row.texPath) ?? "—"}
                                                </td>
                                                <td className="px-5 py-4 text-[13px] text-muted-foreground">
                                                    {row.lastActivityNote || `Submitted ${ago(row.submittedAt)}`}
                                                </td>
                                                <td className="px-5 py-4 text-[13px]">
                                                    <FollowUp row={row} />
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        ) : (
                            <PanelBody className="py-6 text-[13.5px] text-muted-foreground">
                                Nothing submitted yet. A staged application moves here when you confirm, in
                                the extension, that you pressed Submit.
                            </PanelBody>
                        )}
                    </Panel>
                </>
            ) : null}
        </>
    );
}

/** The posting's form, where the extension takes over. A job with no known URL has nowhere to open. */
function OpenAndAutofill({ url }) {
    if (!url) {
        return (
            <Tooltip content="No application or listing URL is stored for this job." align="end" className="shrink-0">
                <span className={cn(buttonVariants({ variant: "attention" }), "pointer-events-none opacity-50")}>
                    <ExternalLink />
                    Open &amp; autofill
                </span>
            </Tooltip>
        );
    }
    return (
        <a href={url} target="_blank" rel="noopener noreferrer" className={buttonVariants({ variant: "attention" })}>
            <ExternalLink />
            Open &amp; autofill
        </a>
    );
}

/** Sent beats due; a due date today or past is the one to act on, so it is the one highlighted. */
function FollowUp({ row }) {
    if (CLOSED.has(row.status)) return <span className="text-muted-foreground">—</span>;
    if (row.followUpSentAt) return <span className="text-muted-foreground">Sent {ago(row.followUpSentAt)}</span>;
    if (!row.followUpDueAt) return <span className="text-muted-foreground">—</span>;

    const days = Math.ceil((new Date(row.followUpDueAt).getTime() - Date.now()) / 86_400_000);
    if (days <= 0) return <span className="font-medium text-primary">{days < 0 ? `Nudge — ${-days}d overdue` : "Nudge today"}</span>;
    return <span className="text-muted-foreground">Nudge in {days}d</span>;
}

function Tally({ n, label, tone }) {
    return (
        <div>
            <div
                className={cn(
                    "text-[22px] font-semibold leading-none",
                    tone === "attention" ? "text-attention-muted" : "text-foreground"
                )}
            >
                {n}
            </div>
            <div className="mt-1.5 text-[12px] text-muted-foreground">{label}</div>
        </div>
    );
}

function fileName(path) {
    return path ? path.split("/").pop() : null;
}

function ago(timestamp) {
    if (!timestamp) return "recently";
    const minutes = Math.round((Date.now() - new Date(timestamp).getTime()) / 60000);
    if (minutes < 60) return minutes < 1 ? "just now" : `${minutes}m ago`;
    if (minutes < 60 * 24) return `${Math.round(minutes / 60)}h ago`;
    if (minutes < 60 * 24 * 30) return `${Math.round(minutes / (60 * 24))}d ago`;
    return new Date(timestamp).toLocaleDateString(undefined, { dateStyle: "medium" });
}
