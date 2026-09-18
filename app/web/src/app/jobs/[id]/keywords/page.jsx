"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { AlertTriangle, ArrowRight, Check, ChevronLeft, Loader2, Quote } from "lucide-react";

import { ApiError, getJob, getMatch, getShellCounts, recordSelection, skipSelection } from "@/services";
import { Badge } from "@/component/ui/badge";
import { Button, buttonVariants } from "@/component/ui/button";
import { Checkbox } from "@/component/ui/checkbox";
import { Panel, PanelBody, PanelHeader, PanelTitle } from "@/component/ui/panel";
import { AppShell } from "@/layout/AppShell";
import { MatchScore } from "@/component/MatchScore";
import { toast } from "@/component/ui/toast";
import { ROUTES, sectionFor } from "@/routes";
import { cn } from "@/util/helper";

/**
 * The keyword gate (FR-7.3). Nothing downstream runs until the user answers here,
 * and the server refuses a resume built on a keyword this screen did not send.
 *
 * Fetching happens in the component rather than the route file because the bearer
 * token lives in sessionStorage, which a server-rendered page cannot read.
 */
export default function Page() {
    const { id: jobId } = useParams();
    const from = useSearchParams().get("from") ?? undefined;
    const router = useRouter();

    const [job, setJob] = useState(null);
    const [match, setMatch] = useState(null);
    const [counts, setCounts] = useState({ pending: 0, shortlisted: 0 });
    const [loadError, setLoadError] = useState(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [reopened, setReopened] = useState(false);

    /** FR-2.5 — starts empty, and no code path seeds it. */
    const [selected, setSelected] = useState(() => new Set());

    const fetching = useRef(false);

    useEffect(() => {
        if (fetching.current) return;
        fetching.current = true;

        (async () => {
            try {
                const [row, scored, badges] = await Promise.all([
                    getJob(jobId),
                    getMatch(jobId),
                    getShellCounts(),
                ]);
                setJob(row);
                setMatch(scored);
                setCounts(badges);
            } catch (failure) {
                setLoadError(failure instanceof ApiError ? failure.message : "Could not load this match.");
            } finally {
                setLoading(false);
                fetching.current = false;
            }
        })();
    }, [jobId]);

    const toggle = (key) =>
        setSelected((prev) => {
            const next = new Set(prev);
            next.has(key) ? next.delete(key) : next.add(key);
            return next;
        });

    async function commit() {
        setSaving(true);
        try {
            await recordSelection(jobId, [...selected]);
            router.push(ROUTES.preview(jobId, from));
        } catch (failure) {
            toast.error(failure instanceof ApiError ? failure.message : "Could not save your selection.");
            setSaving(false);
        }
    }

    async function skip() {
        setSaving(true);
        try {
            await skipSelection(jobId);
            router.push(from === "shortlist" ? ROUTES.shortlist : ROUTES.search);
        } catch (failure) {
            toast.error(failure instanceof ApiError ? failure.message : "Could not skip this job.");
            setSaving(false);
        }
    }

    const shell = { active: sectionFor(from), counts: counts };

    if (loading) {
        return (
            <AppShell {...shell}>
                <Panel className="flex items-center gap-3 p-6 text-[14px] text-muted-foreground">
                    <Loader2 className="size-4 animate-spin" />
                    Loading the match…
                </Panel>
            </AppShell>
        );
    }

    if (loadError || !job) {
        return (
            <AppShell {...shell}>
                <Panel className="p-6">
                    <p className="text-[14px] text-muted-foreground">{loadError ?? "This job no longer exists."}</p>
                </Panel>
            </AppShell>
        );
    }

    // No match row means the scoring step has not run for this job yet. There is
    // nothing to choose between, and inventing keywords to show would be the exact
    // failure this screen exists to prevent.
    if (!match) {
        return (
            <AppShell {...shell}>
                <BackLink jobId={jobId} from={from} />
                <Panel className="p-6">
                    <h1 className="text-[20px] font-semibold tracking-tight">Not scored yet</h1>
                    <p className="mt-2 max-w-[70ch] text-[14px] leading-relaxed text-muted-foreground">
                        <span className="font-medium text-foreground">{job.title}</span> at {job.company.name} has
                        not been matched against your resume. Once it has, the keywords it asks for appear here for
                        you to choose from.
                    </p>
                </Panel>
            </AppShell>
        );
    }

    const review = match.review;
    const answered = review.state !== "pending" && !reopened;
    const count = selected.size;

    return (
        <AppShell {...shell}>
            <div className="mb-5 flex flex-wrap items-center gap-4">
                <BackLink jobId={jobId} from={from} />
                <span className="grow" />
                <MatchScore value={match.score} size="sm" />
                <span className="text-[13px] text-muted-foreground">match</span>
            </div>

            <Panel className="p-6">
                <h1 className="text-[24px] font-semibold leading-tight tracking-tight">
                    Choose what goes into your resume
                </h1>
                <p className="mt-2 max-w-[74ch] text-[14px] leading-relaxed text-pretty text-muted-foreground">
                    <span className="font-medium text-foreground">{job.title}</span> at {job.company.name}. Nothing
                    below is added unless you check it — the keywords on the left are already in your resume and
                    shown for context only.
                </p>
                {match.modelName ? (
                    <p className="mt-3 text-[12px] text-muted-foreground">Scored by {match.modelName}</p>
                ) : null}
            </Panel>

            {answered ? (
                <AnsweredBanner
                    review={review}
                    missing={match.missing}
                    onReopen={() => {
                        // Reopening starts from nothing checked, same as the first
                        // pass. Restoring the old ticks would put marks on the screen
                        // that this visit did not put there. (FR-2.5)
                        setSelected(new Set());
                        setReopened(true);
                    }}
                    jobId={jobId}
                    from={from}
                />
            ) : null}

            <div className="mt-5 grid gap-5 xl:grid-cols-[minmax(0,0.85fr)_minmax(0,1fr)]">
                <Panel className="self-start">
                    <PanelHeader>
                        <PanelTitle>Already in your resume</PanelTitle>
                        <Badge variant="soft">{match.present.length}</Badge>
                        <span className="grow" />
                        <span className="text-[12px] text-muted-foreground">read-only</span>
                    </PanelHeader>
                    <PanelBody>
                        {match.present.length === 0 ? (
                            <p className="text-[13px] text-muted-foreground">
                                Nothing this job asks for is in your resume yet.
                            </p>
                        ) : (
                            <div className="flex flex-wrap gap-2">
                                {match.present.map((keyword) => (
                                    <span
                                        key={keyword.label}
                                        className="inline-flex items-center gap-1.5 rounded-sm bg-primary-tint px-2.5 py-1.5 text-[13px] text-accent-foreground"
                                    >
                                        <Check className="size-[12px] stroke-[3]" />
                                        {keyword.label}
                                    </span>
                                ))}
                            </div>
                        )}
                    </PanelBody>
                </Panel>

                <div className="flex flex-col gap-5">
                    <Panel>
                        <PanelHeader>
                            <PanelTitle>Missing from your resume</PanelTitle>
                            <Badge variant="outline">{match.missing.length}</Badge>
                            <span className="grow" />
                            <span className="text-[12px] font-medium text-attention-muted">
                                none selected by default
                            </span>
                        </PanelHeader>
                        {match.missing.length === 0 ? (
                            <PanelBody>
                                <p className="text-[13px] text-muted-foreground">
                                    Your resume already covers everything this job names.
                                </p>
                            </PanelBody>
                        ) : (
                            <ul>
                                {match.missing.map((keyword, i) => {
                                    const checked = selected.has(keyword.key);
                                    return (
                                        <li key={keyword.key}>
                                            <button
                                                type="button"
                                                disabled={answered || saving}
                                                onClick={() => toggle(keyword.key)}
                                                className={cn(
                                                    "flex w-full items-start gap-3.5 px-5 py-4 text-left transition-colors",
                                                    i < match.missing.length - 1 && "border-b border-border",
                                                    checked ? "bg-primary-wash" : "hover:bg-secondary/60",
                                                    answered && "opacity-60"
                                                )}
                                            >
                                                <Checkbox
                                                    checked={checked}
                                                    onCheckedChange={() => toggle(keyword.key)}
                                                    className="pointer-events-none mt-0.5"
                                                />
                                                <div className="min-w-0 grow">
                                                    <div className="flex flex-wrap items-center gap-2.5">
                                                        <span
                                                            className={cn(
                                                                "text-[14.5px]",
                                                                checked ? "font-medium text-foreground" : "text-foreground"
                                                            )}
                                                        >
                                                            {keyword.label}
                                                        </span>
                                                        <Badge variant="muted">
                                                            {keyword.mentions} {keyword.mentions === 1 ? "mention" : "mentions"}
                                                        </Badge>
                                                    </div>
                                                    <p className="mt-2 inline-flex items-start gap-2 rounded-sm bg-secondary px-2.5 py-1.5 font-mono text-[12px] leading-relaxed text-pretty text-muted-foreground">
                                                        <Quote className="mt-0.5 size-[11px] shrink-0" />
                                                        {keyword.evidence}
                                                    </p>
                                                </div>
                                            </button>
                                        </li>
                                    );
                                })}
                            </ul>
                        )}
                    </Panel>

                    {/* RISK — not selectable */}
                    {match.risks.length > 0 ? (
                        <Panel className="overflow-hidden">
                            <div className="flex items-center gap-3 bg-risk px-5 py-3.5">
                                <AlertTriangle className="size-[15px] shrink-0 text-risk-ink" />
                                <h2 className="text-[14px] font-medium text-risk-ink">Risk flags</h2>
                                <Badge variant="risk">{match.risks.length}</Badge>
                                <span className="grow" />
                                <span className="text-[12px] text-risk-muted">not selectable</span>
                            </div>
                            <div>
                                {match.risks.map((risk, i) => (
                                    <div
                                        key={risk.key}
                                        className={cn("px-5 py-4", i < match.risks.length - 1 && "border-b border-border")}
                                    >
                                        <p className="text-[13.5px] font-medium">{risk.title}</p>
                                        <p className="mt-1.5 text-[13px] leading-relaxed text-pretty text-muted-foreground">
                                            {risk.detail}
                                        </p>
                                    </div>
                                ))}
                            </div>
                        </Panel>
                    ) : null}
                </div>
            </div>

            {answered ? null : (
                <Panel className="sticky bottom-5 mt-5 p-4">
                    <div className="flex flex-wrap items-center gap-x-5 gap-y-3">
                        <div
                            className={cn(
                                "grid size-11 shrink-0 place-items-center rounded-md text-[18px] font-bold",
                                count === 0 ? "bg-secondary text-muted-foreground" : "bg-primary text-primary-foreground"
                            )}
                        >
                            {count}
                        </div>
                        <div className="min-w-0">
                            <p className="text-[14px] font-medium">
                                {count === 0 ? "Nothing selected yet" : `keyword${count === 1 ? "" : "s"} selected`}
                            </p>
                            <p className="mt-0.5 text-[12.5px] text-muted-foreground">
                                Only what you check is written into the .tex — no wording is invented.
                            </p>
                        </div>
                        <span className="grow" />
                        <Button variant="outline" size="sm" disabled={saving} onClick={skip}>
                            Skip this job
                        </Button>
                        <Button size="sm" disabled={count === 0 || saving} onClick={commit}>
                            {saving ? <Loader2 className="animate-spin" /> : null}
                            {count === 0 ? "Tailor resume" : `Tailor with ${count} selected`}
                            <ArrowRight />
                        </Button>
                    </div>
                </Panel>
            )}
        </AppShell>
    );
}

function BackLink({ jobId, from }) {
    return (
        <Link
            href={ROUTES.job(jobId, from)}
            className="inline-flex items-center gap-1.5 text-[13.5px] text-muted-foreground hover:text-primary"
        >
            <ChevronLeft className="size-4" />
            Back to job
        </Link>
    );
}

/** What the user already answered, and the two ways on from it. */
function AnsweredBanner({ review, missing, onReopen, jobId, from }) {
    const labels = missing.filter((keyword) => review.selectedKeys.includes(keyword.key)).map((k) => k.label);

    return (
        <Panel className="mt-5 p-5">
            <p className="text-[14px] font-medium">
                {review.state === "skipped"
                    ? "You skipped this job"
                    : `You chose ${labels.length} keyword${labels.length === 1 ? "" : "s"}`}
            </p>
            {labels.length > 0 ? (
                <div className="mt-3 flex flex-wrap gap-2">
                    {labels.map((label) => (
                        <Badge key={label} variant="soft">
                            {label}
                        </Badge>
                    ))}
                </div>
            ) : null}
            <div className="mt-4 flex flex-wrap items-center gap-3">
                <Button variant="outline" size="sm" onClick={onReopen}>
                    Choose again
                </Button>
                <Link href={ROUTES.preview(jobId, from)} className={buttonVariants({ size: "sm" })}>
                    See the tailored resume
                    <ArrowRight />
                </Link>
            </div>
            <p className="mt-3 text-[12.5px] text-muted-foreground">
                Choosing again starts from nothing checked, the same as the first time.
            </p>
        </Panel>
    );
}
