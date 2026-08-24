import { CheckCheck, ExternalLink, Lock, RefreshCw, Send, Timer } from "lucide-react";
import { AppShell } from "@/layout/AppShell";
import { PageHeader } from "@/layout/PageHeader";
import { StatCard } from "@/component/StatCard";
import { StatusChip } from "@/component/StatusChip";
import { FilePath } from "@/component/FilePath";
import { Panel, PanelBody, PanelHeader, PanelTitle } from "@/component/ui/panel";
import { Button, buttonVariants } from "@/component/ui/button";
import { ROUTES } from "@/routes";
import applications from "@/data/applications.json";
import board from "@/data/board.json";
import search from "@/data/search.json";
import { cn } from "@/util/cn";

export default function Page() {
    const { staged, submitted } = applications;
    const counts = {
        interview: submitted.filter((a) => a.status === "Interview").length,
        active: submitted.filter((a) => a.status !== "Rejected").length,
    };

    return (
        <AppShell
            active={ROUTES.applications}
            counts={{
        pending: board.pending.keywordSelections + board.pending.applicationsToSubmit,
        shortlisted: search.shortlistedCount,
      }}
        >
            <PageHeader
                title="Applications"
                subtitle="One staged and waiting on you. JobPilot fills forms and stops — you submit."
            >
                <Button variant="outline" size="sm">
                    <RefreshCw />
                    Sync sheet
                </Button>
            </PageHeader>

            <div className="grid gap-5 sm:grid-cols-3">
                <StatCard icon={Lock} value={1} label="Staged for you" tone="attention" />
                <StatCard icon={Send} value={counts.active} label="Active applications" />
                <StatCard icon={CheckCheck} value={counts.interview} label="In interview" tone="muted" />
            </div>

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

                <PanelBody className="flex flex-wrap items-center gap-x-8 gap-y-5 py-5">
                    <div className="min-w-[240px]">
                        <h3 className="text-[16px] font-medium">{staged.role}</h3>
                        <p className="mt-1 text-[13px] text-muted-foreground">
                            {staged.company} · {staged.location} · {staged.ats}
                        </p>
                    </div>

                    <div className="flex items-center gap-7">
                        <Tally n={staged.fieldsMatched} label="fields matched" />
                        <Tally n={staged.needsAnswer} label="need you" tone="attention" />
                    </div>

                    <div className="min-w-[280px]">
                        <p className="mb-2 text-[12px] text-muted-foreground">attach by hand</p>
                        <FilePath path={staged.file} />
                    </div>

                    <span className="grow" />
                    <span className={buttonVariants({ variant: "attention" })}>
                        <ExternalLink />
                        Open &amp; autofill
                    </span>
                </PanelBody>
            </Panel>

            {/* SUBMITTED */}
            <Panel className="mt-5 overflow-hidden">
                <PanelHeader>
                    <PanelTitle>Submitted</PanelTitle>
                    <span className="text-[13px] text-muted-foreground">{submitted.length}</span>
                    <span className="grow" />
                    <span className="inline-flex items-center gap-1.5 text-[12.5px] text-muted-foreground">
                        <Timer className="size-[13px]" />
                        synced 4 min ago
                    </span>
                </PanelHeader>

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
                            {submitted.map((app, i) => (
                                <tr
                                    key={app.id}
                                    className={cn(
                                        "transition-colors hover:bg-secondary/50",
                                        i < submitted.length - 1 && "border-b border-border",
                                        app.status === "Rejected" && "opacity-55"
                                    )}
                                >
                                    <td className="px-5 py-4">
                                        <p className="text-[14px] font-medium">{app.role}</p>
                                        <p className="mt-0.5 text-[12.5px] text-muted-foreground">{app.company}</p>
                                    </td>
                                    <td className="px-5 py-4"><StatusChip status={app.status} /></td>
                                    <td className="px-5 py-4 font-mono text-[12px] text-muted-foreground">
                                        {app.file}
                                    </td>
                                    <td className="px-5 py-4 text-[13px] text-muted-foreground">{app.activity}</td>
                                    <td className="px-5 py-4 text-[13px]">
                                        {app.followUp ? (
                                            <span
                                                className={cn(
                                                    app.followUp.startsWith("Nudge")
                                                        ? "font-medium text-primary"
                                                        : "text-muted-foreground"
                                                )}
                                            >
                                                {app.followUp}
                                            </span>
                                        ) : (
                                            <span className="text-muted-foreground">—</span>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </Panel>
        </AppShell>
    );
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
