"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import {
    AlertTriangle, ArrowRight, Briefcase, Building2, CalendarClock, Clock, ExternalLink,
    Hash, Laptop, Loader2, MapPin, Sparkles, Users, Wallet,
} from "lucide-react";
import { MatchScore } from "@/component/MatchScore";
import { Signal } from "@/component/Signal";
import { Badge } from "@/component/ui/badge";
import { Panel, PanelBody, PanelHeader, PanelTitle } from "@/component/ui/panel";
import { Button, buttonVariants } from "@/component/ui/button";
import { Tooltip } from "@/component/ui/tooltip";
import { ShortlistButton } from "@/component/ShortlistButton";
import { useAnalysis } from "@/component/Analysis";
import {
    ApiError,
    getJobDetails,
    setShortlisted,
} from "@/services";
import { useRefreshShell } from "@/hooks/useShellCounts";
import { ROUTES } from "@/routes";
import { renderMarkdown } from "@/util/markdown";
import { cn } from "@/util/helper";

const JOB_TYPE = { full_time: "Full-time", contract: "Contract", part_time: "Part-time", internship: "Internship" };
const WORK_MODE = { on_site: "On-site", hybrid: "Hybrid", remote: "Remote" };
const SOURCE = { career_page: "Career page", linkedin: "LinkedIn", indeed: "Indeed", naukri: "Naukri", serpapi: "Google" };

/**
 * Job details, from the database through the API: the job, its stored description
 * (markdown, rendered here), and the match if the job has been analyzed. A client page
 * because the bearer token lives in sessionStorage.
 *
 * Laid out as designed. Where the design showed data that is not collected — a company profile, a structured summary — the page shows the
 * full posting instead and says what is missing, rather than filling the gap.
 */
export default function Page() {
    const { id: jobId } = useParams();
    const from = useSearchParams().get("from") ?? undefined;

    const [data, setData] = useState({ status: "loading" });
    const fetching = useRef(false);

    const load = useCallback(async () => {
        try {
            // One request: the posting, its description, and your own match and shortlist.
            const job = await getJobDetails(jobId);
            setData(
                job
                    ? {
                          status: "ready",
                          job,
                          description: job.description,
                          match: job.match,
                          shortlisted: job.shortlisted,
                      }
                    : { status: "missing" }
            );
        } catch (failure) {
            setData({ status: "error", error: failure instanceof ApiError ? failure.message : "Could not load this job." });
        }
    }, [jobId]);

    useEffect(() => {
        // A ref, not state: React's development double-mount fires the effect twice.
        if (fetching.current) return;
        fetching.current = true;
        load();
    }, [load]);

    const refreshShell = useRefreshShell();
    // An analysis ends with a reload, so the score appears — and a new keyword choice
    // waits in the header and sidebar badges.
    const analysis = useAnalysis(
        useCallback(async () => {
            await load();
            await refreshShell();
        }, [load, refreshShell])
    );

    return (
        <>
            {data.status === "loading" ? <p className="text-[13px] text-muted-foreground">Loading the job…</p> : null}
            {data.status === "error" ? <Problem>{data.error}</Problem> : null}
            {data.status === "missing" ? <Problem>This job no longer exists.</Problem> : null}
            {data.status === "ready" ? (
                <JobDetails {...data} jobId={jobId} from={from} analysis={analysis} onShortlisted={refreshShell} />
            ) : null}
        </>
    );
}

function JobDetails({ job, description, match, shortlisted, jobId, from, analysis, onShortlisted }) {
    const html = useMemo(() => (description?.jdText ? renderMarkdown(description.jdText) : ""), [description]);
    const analyzing = analysis.running && analysis.run?.jobIds.includes(jobId);
    const pending = match?.review?.state === "pending";
    const host = hostOf(job.listingUrl ?? description?.url);

    return (
        <>
            {/* header panel */}
            <Panel className="p-6">
                <div className="flex flex-wrap items-start gap-x-6 gap-y-5">
                    <span className="grid size-16 shrink-0 place-items-center rounded-md bg-secondary text-muted-foreground">
                        <Building2 className="size-7" />
                    </span>

                    <div className="min-w-[260px] flex-1">
                        <h1 className="text-[26px] font-semibold leading-tight tracking-tight">{job.title}</h1>
                        <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-2">
                            <p className="text-[15px] text-muted-foreground">{job.company}</p>
                            {job.jobType ? <Badge variant="soft">{JOB_TYPE[job.jobType]}</Badge> : null}
                            <Badge variant="source">{SOURCE[job.source] ?? job.source}</Badge>
                        </div>
                        <div className="mt-3.5 flex flex-wrap items-center gap-x-5 gap-y-2 text-[13.5px] text-muted-foreground">
                            <Meta icon={MapPin}>{job.location}</Meta>
                            <Meta icon={Clock}>
                                {job.postedAt ? `Posted ${ago(job.postedAt)}` : `Found ${ago(job.discoveredAt)}`}
                            </Meta>
                            {job.salaryText ? <Meta icon={Wallet}>{job.salaryText}</Meta> : null}
                            {job.experienceBand ? <Meta icon={Briefcase}>{job.experienceBand}</Meta> : null}
                            {job.workMode ? <Meta icon={Laptop}>{WORK_MODE[job.workMode]}</Meta> : null}
                        </div>
                    </div>

                    <div className="flex shrink-0 flex-col items-center gap-3">
                        {match ? (
                            <MatchScore value={match.score} size="lg" />
                        ) : (
                            <Tooltip content="Not compared with your resume yet" align="end">
                                <MatchScore value={null} size="lg" />
                            </Tooltip>
                        )}
                        <span className="text-[12px] text-muted-foreground">match</span>
                    </div>
                </div>

                <div className="mt-6 flex flex-wrap items-center gap-3 border-t border-border pt-5">
                    {match ? (
                        <Link href={ROUTES.keywords(jobId, from)} className={buttonVariants()}>
                            Review keywords
                            <ArrowRight />
                        </Link>
                    ) : (
                        <AnalyzeButton jobId={jobId} analysis={analysis} analyzing={analyzing} />
                    )}
                    {job.listingUrl ? (
                        <a
                            href={job.listingUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className={buttonVariants({ variant: "outline" })}
                        >
                            <ExternalLink />
                            Open original posting
                        </a>
                    ) : null}
                    <ShortlistButton
                        shortlisted={shortlisted}
                        onToggle={async (next) => {
                            await setShortlisted(jobId, next);
                            await onShortlisted();
                        }}
                    />
                    <span className="grow" />
                    {job.deadlineAt ? (
                        <span className="inline-flex items-center gap-1.5 text-[13px] text-muted-foreground">
                            <CalendarClock className="size-[14px]" />
                            Closes {new Date(job.deadlineAt).toLocaleDateString(undefined, { dateStyle: "medium" })}
                        </span>
                    ) : null}
                </div>
                {analysis.error ? <p className="mt-3 text-[12.5px] text-risk-ink">{analysis.error}</p> : null}
            </Panel>

            <div className="mt-5 grid gap-5 xl:grid-cols-[minmax(0,1fr)_340px]">
                {/* JD body */}
                <div className="flex flex-col gap-5">
                    <Panel>
                        <PanelHeader>
                            <PanelTitle>Job description</PanelTitle>
                        </PanelHeader>
                        <PanelBody>
                            {html ? (
                                // Escaped by markdown-it (html: false) — see util/markdown.js.
                                <div className="jd-body" dangerouslySetInnerHTML={{ __html: html }} />
                            ) : (
                                <p className="text-[13.5px] text-muted-foreground">
                                    No description is stored for this job.
                                    {job.listingUrl ? " Open the original posting to read it." : ""}
                                </p>
                            )}
                        </PanelBody>
                    </Panel>

                    <Panel>
                        <PanelHeader>
                            <PanelTitle>Tech stack</PanelTitle>
                        </PanelHeader>
                        <PanelBody>
                            {job.techStack?.length ? (
                                <div className="flex flex-wrap gap-1.5">
                                    {job.techStack.map((item) => (
                                        <Badge key={item} variant="soft">{item}</Badge>
                                    ))}
                                </div>
                            ) : job.techStack ? (
                                <p className="text-[13.5px] text-muted-foreground">
                                    This posting names no specific technology.
                                </p>
                            ) : (
                                <div className="flex flex-col items-start gap-3">
                                    <p className="text-[13.5px] text-muted-foreground">
                                        The technologies this posting names are read when the job is analyzed.
                                    </p>
                                    {/* Scored before the stack existed: Analyze now reads only the stack. */}
                                    {match ? (
                                        <AnalyzeButton jobId={jobId} analysis={analysis} analyzing={analyzing} />
                                    ) : null}
                                </div>
                            )}
                        </PanelBody>
                    </Panel>

                    {/* the agent's read on this JD — what makes this page JobPilot's, not a job board's */}
                    <Panel>
                        <PanelHeader>
                            <PanelTitle>What the match agent found</PanelTitle>
                            <span className="grow" />
                            {match ? (
                                <Link
                                    href={ROUTES.keywords(jobId, from)}
                                    className="text-[13px] font-medium text-primary hover:underline"
                                >
                                    Review &amp; select
                                </Link>
                            ) : null}
                        </PanelHeader>
                        <PanelBody className="flex flex-col gap-5">
                            {match ? (
                                <MatchFindings match={match} />
                            ) : (
                                <p className="text-[13.5px] leading-relaxed text-muted-foreground">
                                    {analyzing
                                        ? "Comparing this job with your resume — about a minute."
                                        : "Not compared with your resume yet. Analyze the job to see which of its requirements your resume covers, which are missing, and any risks."}
                                </p>
                            )}
                        </PanelBody>
                    </Panel>
                </div>

                {/* company rail — adapted from the reference's employer-details page */}
                <div className="flex flex-col gap-5">
                    <Panel>
                        <PanelHeader><PanelTitle>Company</PanelTitle></PanelHeader>
                        <PanelBody className="flex flex-col gap-4">
                            <div className="flex items-center gap-3">
                                <span className="grid size-12 shrink-0 place-items-center rounded-md bg-secondary text-muted-foreground">
                                    <Building2 className="size-5" />
                                </span>
                                <div className="min-w-0">
                                    <p className="truncate text-[15px] font-medium">{job.company}</p>
                                    {host ? <p className="truncate text-[12.5px] text-muted-foreground">via {host}</p> : null}
                                </div>
                            </div>
                            <p className="text-[12.5px] leading-relaxed text-muted-foreground">
                                Industry, size and a company profile are not collected yet.
                            </p>
                            <dl className="flex flex-col divide-y divide-border">
                                <Row icon={Laptop} label="Workplace">{WORK_MODE[job.workMode] ?? "—"}</Row>
                                <Row icon={Briefcase} label="Experience">{job.experienceBand ?? "—"}</Row>
                                <Row icon={Wallet} label="Salary">{job.salaryText ?? "—"}</Row>
                                <Row icon={Users} label="Applicants">{job.applicantCount ?? "—"}</Row>
                                {job.refId ? <Row icon={Hash} label="Requisition">{job.refId}</Row> : null}
                            </dl>
                        </PanelBody>
                    </Panel>

                    <Panel>
                        <PanelHeader><PanelTitle>Next step</PanelTitle></PanelHeader>
                        <PanelBody className="flex flex-col gap-3">
                            <p className="text-[13.5px] leading-relaxed text-muted-foreground">
                                {match
                                    ? "Selecting keywords is the only way a resume gets tailored for this job. Nothing is written without your explicit choice."
                                    : "Analyze the job first: it is compared with your resume, and the keywords it is missing become yours to choose from."}
                            </p>
                            {match ? (
                                <Link href={ROUTES.keywords(jobId, from)} className={cn(buttonVariants(), "w-full")}>
                                    {pending
                                        ? `Review ${match.missing.length} missing keywords`
                                        : "See your keyword choice"}
                                </Link>
                            ) : (
                                <AnalyzeButton jobId={jobId} analysis={analysis} analyzing={analyzing} wide />
                            )}
                        </PanelBody>
                    </Panel>
                </div>
            </div>
        </>
    );
}

function MatchFindings({ match }) {
    return (
        <>
            <div>
                <p className="mb-2.5 text-[13px] font-medium">
                    In your resume
                    <span className="ml-2 text-muted-foreground">{match.present.length}</span>
                </p>
                <div className="flex flex-wrap gap-1.5">
                    {match.present.slice(0, 12).map((item) => (
                        <Badge key={item.label} variant="soft">{item.label}</Badge>
                    ))}
                    {match.present.length > 12 ? <Badge variant="muted">+{match.present.length - 12}</Badge> : null}
                    {!match.present.length ? <span className="text-[12.5px] text-muted-foreground">none</span> : null}
                </div>
            </div>
            <div>
                <p className="mb-2.5 text-[13px] font-medium">
                    Missing
                    <span className="ml-2 text-muted-foreground">{match.missing.length}</span>
                    <span className="ml-2 text-[12px] font-normal text-attention-muted">
                        nothing is added unless you check it
                    </span>
                </p>
                <div className="flex flex-wrap gap-1.5">
                    {match.missing.map((item) => (
                        <Badge key={item.key} variant="outline">{item.label}</Badge>
                    ))}
                    {!match.missing.length ? <span className="text-[12.5px] text-muted-foreground">none</span> : null}
                </div>
            </div>
            {match.risks.length ? (
                <div className="flex flex-col gap-2.5">
                    {match.risks.map((risk) => (
                        <Tooltip key={risk.key} content={risk.detail}>
                            <Signal kind="risk" className="items-start">{risk.title}</Signal>
                        </Tooltip>
                    ))}
                </div>
            ) : null}
        </>
    );
}

/** Only offered while the job has no match — a scored job is never analyzed again. */
function AnalyzeButton({ jobId, analysis, analyzing, wide = false }) {
    const busyElsewhere = analysis.running && !analyzing;
    return (
        <Tooltip
            content={busyElsewhere ? "Another analysis is running — try again when it finishes." : "About a minute and ~$0.001."}
            className={wide ? "w-full" : undefined}
        >
            <Button
                className={wide ? "w-full" : undefined}
                disabled={analysis.running}
                onClick={() => analysis.start({ jobIds: [jobId] })}
            >
                {analyzing ? <Loader2 className="animate-spin" /> : <Sparkles />}
                {analyzing ? "Analyzing…" : "Analyze this job"}
            </Button>
        </Tooltip>
    );
}

function Problem({ children }) {
    return (
        <Panel className="flex items-start gap-2 px-5 py-4 text-[13px] text-risk-ink">
            <AlertTriangle className="mt-0.5 size-[14px] shrink-0" />
            {children}
        </Panel>
    );
}

function Meta({ icon: Icon, children }) {
    return (
        <span className="inline-flex items-center gap-1.5">
            <Icon className="size-[14px]" />
            {children}
        </span>
    );
}

function Row({ icon: Icon, label, children }) {
    return (
        <div className="flex items-center gap-3 py-2.5">
            <Icon className="size-[14px] shrink-0 text-muted-foreground" />
            <dt className="text-[13px] text-muted-foreground">{label}</dt>
            <span className="grow" />
            <dd className="text-[13px] font-medium">{children}</dd>
        </div>
    );
}

function hostOf(url) {
    try {
        return url ? new URL(url).hostname : null;
    } catch {
        return null;
    }
}

function ago(timestamp) {
    if (!timestamp) return "recently";
    const minutes = Math.round((Date.now() - new Date(timestamp).getTime()) / 60000);
    if (minutes < 60) return minutes < 1 ? "just now" : `${minutes}m ago`;
    if (minutes < 60 * 24) return `${Math.round(minutes / 60)}h ago`;
    if (minutes < 60 * 24 * 30) return `${Math.round(minutes / (60 * 24))}d ago`;
    return new Date(timestamp).toLocaleDateString(undefined, { dateStyle: "medium" });
}
