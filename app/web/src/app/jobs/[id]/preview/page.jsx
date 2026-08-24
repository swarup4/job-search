import Link from "next/link";
import { ArrowRight, ChevronLeft, FileText } from "lucide-react";
import { AppShell } from "@/layout/AppShell";
import { Badge } from "@/component/ui/badge";
import { Panel, PanelHeader, PanelTitle } from "@/component/ui/panel";
import { buttonVariants } from "@/component/ui/button";
import { ROUTES } from "@/routes";
import diff from "@/data/diff.json";
import board from "@/data/board.json";
import { cn } from "@/util/cn";

export default async function Page({ params }) {
  const { id: jobId } = await params;

    return (
        <AppShell
            active={ROUTES.shortlist}
            counts={{ pending: board.pending.keywordSelections + board.pending.applicationsToSubmit }}
        >
            <div className="mb-5 flex flex-wrap items-center gap-4">
                <Link
                    href={ROUTES.keywords(jobId)}
                    className="inline-flex items-center gap-1.5 text-[13.5px] text-muted-foreground hover:text-primary"
                >
                    <ChevronLeft className="size-4" />
                    Back to keywords
                </Link>
                <span className="grow" />
                <span className="inline-flex items-center gap-2 rounded-sm bg-secondary px-2.5 py-1.5 font-mono text-[12px] text-muted-foreground">
                    <FileText className="size-[12px]" />
                    {diff.file}
                </span>
            </div>

            <Panel className="p-6">
                <div className="flex flex-wrap items-center gap-x-6 gap-y-4">
                    <div className="min-w-[280px]">
                        <h1 className="text-[24px] font-semibold leading-tight tracking-tight">
                            Review the tailored resume
                        </h1>
                        <p className="mt-2 text-[14px] text-muted-foreground">
                            {diff.added} additions across two sections. Nothing else changed.
                        </p>
                    </div>
                    <span className="grow" />
                    <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
                        <span className="text-[13px] text-muted-foreground">incorporated</span>
                        {diff.incorporated.map((kw) => (
                            <Badge key={kw} variant="soft">{kw}</Badge>
                        ))}
                        <span className="text-[13px] text-muted-foreground">declined</span>
                        <Badge variant="muted" className="line-through">{diff.declined}</Badge>
                    </div>
                </div>
            </Panel>

            <Panel className="mt-5 overflow-hidden">
                <PanelHeader>
                    <PanelTitle>Diff</PanelTitle>
                    <span className="ml-1 font-mono text-[12px] text-muted-foreground">
                        {diff.from} → {diff.file}
                    </span>
                    <span className="grow" />
                    <Badge variant="muted" className="text-added-gutter">+{diff.added}</Badge>
                    <Badge variant="muted">−{diff.removed}</Badge>
                </PanelHeader>

                <div className="overflow-x-auto py-3">
                    {diff.hunks.map((line, i) =>
                        line.gap ? (
                            <div key={`gap-${i}`} className="my-2 ml-12 h-px bg-border" />
                        ) : (
                            <div
                                key={line.n}
                                className={cn(
                                    "flex font-mono text-[12.5px] leading-[24px]",
                                    line.add && "bg-added"
                                )}
                            >
                                <span
                                    className={cn(
                                        "w-12 shrink-0 select-none pr-3 text-right text-[11px]",
                                        line.add ? "text-added-gutter" : "text-muted-foreground/55"
                                    )}
                                >
                                    {line.n}
                                </span>
                                <span
                                    className={cn(
                                        "w-4 shrink-0 select-none text-center",
                                        line.add && "font-semibold text-added-gutter"
                                    )}
                                >
                                    {line.add ? "+" : ""}
                                </span>
                                <span
                                    className={cn(
                                        "whitespace-pre pr-5",
                                        line.add ? "text-added-ink" : "text-muted-foreground"
                                    )}
                                >
                                    {line.text}
                                </span>
                            </div>
                        )
                    )}
                </div>

                <div className="border-t border-border bg-well px-5 py-3">
                    <p className="text-[12.5px] text-muted-foreground">
                        <span className="font-mono">{diff.declined}</span> was offered but you left it
                        unchecked, so it does not appear.
                    </p>
                </div>
            </Panel>

            <Panel className="mt-5 p-4">
                <div className="flex flex-wrap items-center gap-x-5 gap-y-3">
                    <div>
                        <p className="text-[14px] font-medium">.tex source only — no PDF is compiled</p>
                        <p className="mt-0.5 font-mono text-[12px] text-muted-foreground">
                            ~/jobpilot/resumes/{diff.file}
                        </p>
                    </div>
                    <span className="grow" />
                    <Link
                        href={ROUTES.keywords(jobId)}
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
