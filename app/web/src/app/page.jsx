import Link from "next/link";
import { Briefcase, CheckCheck, FileCheck2, Send, ArrowRight } from "lucide-react";
import { AppShell } from "@/layout/AppShell";
import { PageHeader } from "@/layout/PageHeader";
import { StatCard } from "@/component/StatCard";
import { PipelineColumn } from "@/component/PipelineColumn";
import { Panel } from "@/component/ui/panel";
import { buttonVariants } from "@/component/ui/button";
import { ROUTES } from "@/routes";
import board from "@/data/board.json";
import { cn } from "@/util/cn";

export default function Page() {
    const { pending, columns } = board;
    const total = pending.keywordSelections + pending.applicationsToSubmit;
    const byKey = Object.fromEntries(columns.map((c) => [c.key, c.count]));

    return (
        <AppShell
            active={ROUTES.board}
            counts={{ pending: total, newJobs: byKey.new }}
        >
            <PageHeader
                title="Pipeline"
                subtitle="Every job the agents found, and where each one stands."
            />

            <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
                <StatCard icon={Briefcase} value={byKey.new} label="New this morning" />
                <StatCard icon={CheckCheck} value={byKey.reviewed} label="Reviewed" tone="muted" />
                <StatCard icon={FileCheck2} value={byKey.tailored} label="Resumes tailored" tone="muted" />
                <StatCard icon={Send} value={byKey.applied} label="Applied" tone="muted" />
            </div>

            {/* the approval gate — the one coloured surface on the page */}
            {total > 0 ? (
                <Panel className="mt-5 overflow-hidden">
                    <div className="flex flex-wrap items-center gap-x-5 gap-y-3 bg-attention px-5 py-4">
                        <div className="grid size-11 shrink-0 place-items-center rounded-md bg-attention-solid text-white">
                            <span className="text-[18px] font-bold">{total}</span>
                        </div>
                        <div className="min-w-0">
                            <p className="text-[16px] font-semibold text-attention-ink">Pending your review</p>
                            <p className="mt-0.5 text-[13px] text-attention-muted">
                                {pending.keywordSelections} keyword selections ·{" "}
                                {pending.applicationsToSubmit} application to submit. Nothing moves forward
                                without you.
                            </p>
                        </div>
                        <span className="grow" />
                        <Link
                            href={ROUTES.applications}
                            className={cn(buttonVariants({ variant: "attentionQuiet", size: "sm" }))}
                        >
                            Review applications
                        </Link>
                        <Link
                            href={ROUTES.keywords("acme")}
                            className={cn(buttonVariants({ variant: "attention", size: "sm" }))}
                        >
                            Select keywords
                            <ArrowRight />
                        </Link>
                    </div>
                </Panel>
            ) : null}

            <div className="mt-6 grid gap-5 md:grid-cols-2 xl:grid-cols-5">
                {columns.map((column) => (
                    <PipelineColumn key={column.key} column={column} />
                ))}
            </div>
        </AppShell>
    );
}
