"use client";

import { useMemo, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import Link from "next/link";
import { ArrowRight, ChevronLeft, FileText } from "lucide-react";
import { AppShell } from "@/layout/AppShell";
import { Badge } from "@/component/ui/badge";
import { Panel } from "@/component/ui/panel";
import { buttonVariants } from "@/component/ui/button";
import { SuggestionPanel } from "@/component/SuggestionPanel";
import { ResumePreview } from "@/component/ResumePreview";
import { ROUTES, sectionFor } from "@/routes";
import { buildDocument } from "@/util/resumeDoc";
import resume from "@/data/resume.json";
import board from "@/data/board.json";
import search from "@/data/search.json";

export default function Page() {
    const { id: jobId } = useParams();
    const from = useSearchParams().get("from") ?? undefined;

    const doc = useMemo(() => buildDocument(resume, jobId), [jobId]);

    const [activeLine, setActiveLine] = useState(null);

    const active = useMemo(
        () => doc.lines.find((line) => line.n === activeLine) ?? null,
        [activeLine, doc]
    );

    return (
        <AppShell
            active={sectionFor(from)}
            counts={{
                pending: board.pending.keywordSelections + board.pending.applicationsToSubmit,
                shortlisted: search.shortlistedCount,
            }}
        >
            <div className="mb-5 flex flex-wrap items-center gap-4">
                <Link
                    href={ROUTES.keywords(jobId, from)}
                    className="inline-flex items-center gap-1.5 text-[13.5px] text-muted-foreground hover:text-primary"
                >
                    <ChevronLeft className="size-4" />
                    Back to keywords
                </Link>
                <span className="grow" />
                <span className="inline-flex items-center gap-2 rounded-sm bg-secondary px-2.5 py-1.5 font-mono text-[12px] text-muted-foreground">
                    <FileText className="size-[12px]" />
                    {doc.file}
                </span>
            </div>

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
                        <span className="text-[13px] text-muted-foreground">incorporated</span>
                        {doc.incorporated.map((kw) => (
                            <Badge key={kw} variant="soft">{kw}</Badge>
                        ))}
                        <span className="text-[13px] text-muted-foreground">declined</span>
                        {doc.declined.map((kw) => (
                            <Badge key={kw} variant="muted" className="line-through">{kw}</Badge>
                        ))}
                    </div>
                </div>
            </Panel>

            <div className="mt-5 grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(340px,400px)]">
                <ResumePreview
                    doc={doc}
                    activeLine={activeLine}
                    onSelect={(n) => setActiveLine((prev) => (prev === n ? null : n))}
                />

                <div className="xl:sticky xl:top-6">
                    <SuggestionPanel
                        keywords={doc.incorporated}
                        activeLine={active}
                        onDismiss={() => setActiveLine(null)}
                    />
                </div>
            </div>

            <Panel className="mt-5 p-4">
                <div className="flex flex-wrap items-center gap-x-5 gap-y-3">
                    <div>
                        <p className="text-[14px] font-medium">Tailored source file</p>
                        <p className="mt-0.5 font-mono text-[12px] text-muted-foreground">
                            ~/jobpilot/resumes/{doc.file}
                        </p>
                    </div>
                    <span className="grow" />
                    <Link
                        href={ROUTES.keywords(jobId, from)}
                        className={buttonVariants({ variant: "outline", size: "sm" })}
                    >
                        Back to keywords
                    </Link>
                    <Link href={ROUTES.applications} className={buttonVariants({ size: "sm" })}>
                        Stage for application
                        <ArrowRight />
                    </Link>
                </div>
            </Panel>
        </AppShell>
    );
}
