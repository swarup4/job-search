"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import Link from "next/link";
import { ArrowRight, ChevronLeft, FileText, Loader2, RefreshCw, Sparkles } from "lucide-react";

import { ApiError, getMatch, getResume, getResumePdf, tailorResume } from "@/services";
import { useRefreshStatus } from "@/hooks/useStatus";
import { Badge } from "@/component/ui/badge";
import { Panel } from "@/component/ui/panel";
import { Button, buttonVariants } from "@/component/ui/button";
import { ResumePreview } from "@/component/ResumePreview";
import { ResumeChat } from "@/component/ResumeChat";
import { toast } from "@/component/ui/toast";
import { ROUTES } from "@/routes";
import { buildDocument } from "@/util/resumeDoc";

function sameKeys(a, b) {
    return a.length === b.length && [...a].sort().join("\n") === [...b].sort().join("\n");
}

/**
 * The tailored resume for one job. Tailoring is always a click — opening this page
 * never starts a model call — and storing the result stages the application.
 */
export default function Page() {
    const { id: jobId } = useParams();
    const from = useSearchParams().get("from") ?? undefined;
    const refreshStatus = useRefreshStatus();

    const [match, setMatch] = useState(null);
    const [resume, setResume] = useState(null);
    const [loading, setLoading] = useState(true);
    const [loadError, setLoadError] = useState(null);
    const [tailoring, setTailoring] = useState(false);
    const [tailorError, setTailorError] = useState(null);

    const fetching = useRef(false);

    useEffect(() => {
        if (fetching.current) return;
        fetching.current = true;

        (async () => {
            try {
                const [scored, stored] = await Promise.all([getMatch(jobId), getResume(jobId)]);
                setMatch(scored);
                setResume(stored);
            } catch (failure) {
                setLoadError(failure instanceof ApiError ? failure.message : "Could not load this resume.");
            } finally {
                setLoading(false);
                fetching.current = false;
            }
        })();
    }, [jobId]);

    const doc = useMemo(() => (resume ? buildDocument(resume) : null), [resume]);

    async function tailor() {
        setTailoring(true);
        setTailorError(null);
        try {
            setResume(await tailorResume(jobId));
            refreshStatus();
        } catch (failure) {
            setTailorError(failure instanceof ApiError ? failure.message : "Could not tailor the resume.");
        } finally {
            setTailoring(false);
        }
    }

    async function downloadPdf() {
        try {
            save(await getResumePdf(jobId), doc.file.replace(/\.tex$/, ".pdf"));
        } catch (failure) {
            toast.error(failure instanceof ApiError ? failure.message : "Could not compile the PDF.");
        }
    }

    if (loading) {
        return (
            <Panel className="flex items-center gap-3 p-6 text-[14px] text-muted-foreground">
                <Loader2 className="size-4 animate-spin" />
                Loading the resume…
            </Panel>
        );
    }

    if (loadError) {
        return (
            <Panel className="p-6">
                <p className="text-[14px] text-muted-foreground">{loadError}</p>
            </Panel>
        );
    }

    const selectedKeys = match?.review.state === "selected" ? match.review.selectedKeys : null;
    const stale = resume && selectedKeys && !sameKeys(resume.selectedKeys, selectedKeys);

    // The server refuses to tailor without an answered keyword gate, so there is
    // nothing to offer here but the way back to it.
    if (!resume && !selectedKeys) {
        return (
            <>
                <TopBar jobId={jobId} from={from} />
                <Panel className="p-6">
                    <h1 className="text-[20px] font-semibold tracking-tight">No keyword selection yet</h1>
                    <p className="mt-2 max-w-[70ch] text-[14px] leading-relaxed text-muted-foreground">
                        A tailored resume only ever adds keywords you ticked. Choose them first, then come back
                        here to tailor.
                    </p>
                    <Link
                        href={ROUTES.keywords(jobId, from)}
                        className={buttonVariants({ size: "sm", className: "mt-4" })}
                    >
                        Select keywords
                        <ArrowRight />
                    </Link>
                </Panel>
            </>
        );
    }

    if (!resume) {
        return (
            <>
                <TopBar jobId={jobId} from={from} />
                <Panel className="p-6">
                    <h1 className="text-[20px] font-semibold tracking-tight">Tailor your resume to this job</h1>
                    <p className="mt-2 max-w-[70ch] text-[14px] leading-relaxed text-muted-foreground">
                        Your default resume gets the {selectedKeys.length} keyword
                        {selectedKeys.length === 1 ? "" : "s"} you selected, each placed in an existing skill group
                        or bullet. A keyword with no honest place is left out and listed as declined. Nothing else
                        changes. One model call, a few seconds.
                    </p>
                    <Button size="sm" className="mt-4" onClick={tailor} disabled={tailoring}>
                        {tailoring ? <Loader2 className="animate-spin" /> : <Sparkles />}
                        {tailoring ? "Tailoring…" : "Tailor resume"}
                    </Button>
                    {tailorError && <p className="mt-3 text-[13.5px] text-risk-ink">{tailorError}</p>}
                </Panel>
            </>
        );
    }

    return (
        <>
            <TopBar jobId={jobId} from={from} file={doc.file} />

            {stale && (
                <Panel className="mb-5 flex flex-wrap items-center gap-x-4 gap-y-3 p-4">
                    <p className="text-[14px]">
                        Your keyword selection changed since this resume was tailored.
                    </p>
                    <span className="grow" />
                    <Button size="sm" onClick={tailor} disabled={tailoring}>
                        {tailoring ? <Loader2 className="animate-spin" /> : <RefreshCw />}
                        {tailoring ? "Tailoring…" : "Re-tailor"}
                    </Button>
                    {tailorError && <p className="basis-full text-[13.5px] text-risk-ink">{tailorError}</p>}
                </Panel>
            )}

            <Panel className="p-6">
                <div className="flex flex-wrap items-center gap-x-6 gap-y-4">
                    <div className="min-w-[280px]">
                        <h1 className="text-[24px] font-semibold leading-tight tracking-tight">
                            Review the tailored resume
                        </h1>
                        <p className="mt-2 text-[14px] text-muted-foreground">
                            {doc.added} line{doc.added === 1 ? "" : "s"} changed from your
                            selections. Nothing else changed.
                        </p>
                    </div>
                    <span className="grow" />
                    <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
                        {doc.incorporated.length > 0 && (
                            <>
                                <span className="text-[13px] text-muted-foreground">incorporated</span>
                                {doc.incorporated.map((kw) => (
                                    <Badge key={kw} variant="soft">{kw}</Badge>
                                ))}
                            </>
                        )}
                        {doc.declined.length > 0 && (
                            <>
                                <span className="text-[13px] text-muted-foreground">declined</span>
                                {doc.declined.map((kw) => (
                                    <Badge key={kw} variant="muted" className="line-through">{kw}</Badge>
                                ))}
                            </>
                        )}
                    </div>
                </div>
            </Panel>

            <div className="mt-5 grid grid-cols-[minmax(0,1fr)] items-start gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(340px,400px)]">
                <ResumePreview doc={doc} onDownloadPdf={downloadPdf} />

                <div className="xl:sticky xl:bottom-6 xl:self-end">
                    <ResumeChat />
                </div>
            </div>

            <Panel className="mt-5 p-4">
                <div className="flex flex-wrap items-center gap-x-5 gap-y-3">
                    <div>
                        <p className="text-[14px] font-medium">
                            Tailored source file · v{resume.version}
                        </p>
                        <p className="mt-0.5 break-all font-mono text-[12px] text-muted-foreground">
                            {doc.filePath}
                        </p>
                    </div>
                    <span className="grow" />
                    <Link
                        href={ROUTES.keywords(jobId, from)}
                        className={buttonVariants({ variant: "outline", size: "sm" })}
                    >
                        Back to keywords
                    </Link>
                    {/* Storing the resume already staged the application; this only goes there. */}
                    <Link href={ROUTES.applications} className={buttonVariants({ size: "sm" })}>
                        Go to Applications
                        <ArrowRight />
                    </Link>
                </div>
            </Panel>
        </>
    );
}

function TopBar({ jobId, from, file }) {
    return (
        <div className="mb-5 flex flex-wrap items-center gap-4">
            <Link
                href={ROUTES.keywords(jobId, from)}
                className="inline-flex items-center gap-1.5 text-[13.5px] text-muted-foreground hover:text-primary"
            >
                <ChevronLeft className="size-4" />
                Back to keywords
            </Link>
            <span className="grow" />
            {file && (
                <span className="inline-flex items-center gap-2 rounded-sm bg-secondary px-2.5 py-1.5 font-mono text-[12px] text-muted-foreground">
                    <FileText className="size-[12px]" />
                    {file}
                </span>
            )}
        </div>
    );
}

/** Same as ResumeReview's: the PDF needs the bearer token, so it cannot be an `<a href>`. */
function save(blob, filename) {
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    anchor.click();
    URL.revokeObjectURL(url);
}
