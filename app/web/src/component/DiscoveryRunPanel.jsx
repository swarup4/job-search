"use client";

import { useSelector } from "react-redux";
import { History } from "lucide-react";

import { useDiscovery } from "@/component/DiscoveryContext";
import { KV } from "@/component/TierSettings";
import { Panel, PanelBody, PanelHeader, PanelTitle } from "@/component/ui/panel";
import { Badge } from "@/component/ui/badge";
import { selectStatus } from "@/store/status/statusSlice";

const STATUS = {
    running: { label: "running", variant: "soft" },
    done: { label: "finished", variant: "outline" },
    failed: { label: "stopped", variant: "risk" },
};

/**
 * When discovery last ran, what it searched for, and what it found.
 *
 * The run itself lives in the AI tier's memory, so a restart there forgets it. Each
 * company's latest result is stored on its career source, though, so after a restart
 * this falls back to the status store's `discovery`, summed from those records.
 */
export function DiscoveryRunPanel() {
    const { run, running } = useDiscovery();
    const { discovery, syncedAt } = useSelector(selectStatus);
    const status = run ? STATUS[run.status] : null;

    return (
        <Panel>
            <PanelHeader>
                <History className="size-[16px] text-primary" />
                <PanelTitle>Last run</PanelTitle>
                <span className="grow" />
                {status ? <Badge variant={status.variant}>{status.label}</Badge> : null}
            </PanelHeader>

            <PanelBody className="flex flex-col gap-3 py-4">
                {run ? (
                    <LiveRun run={run} running={running} />
                ) : (
                    <Recorded discovery={discovery} loaded={Boolean(syncedAt)} />
                )}

                <p className="border-t border-border pt-3 text-[12.5px] leading-relaxed text-muted-foreground">
                    <span className="font-medium text-foreground">When does it run?</span> Only when you
                    press <span className="font-medium text-foreground">Run discovery</span> — there is no
                    schedule yet. Each run searches every enabled company with your saved Search targets,
                    respects robots.txt with at most two requests per site, and skips postings it has
                    already stored.
                </p>
            </PanelBody>
        </Panel>
    );
}

function LiveRun({ run, running }) {
    const totals = sum(run.results);
    const found = run.results.filter((result) => result.new > 0).sort((a, b) => b.new - a.new);
    const skipped = run.results.filter((result) => result.skipped).length;

    return (
        <>
            <KV label="Triggered" value={`${when(run.startedAt)} · by you, from this page`} />
            <KV label="Finished" value={run.finishedAt ? when(run.finishedAt) : "still running"} />
            <KV label="Took" value={duration(run.startedAt, run.finishedAt)} />
            <KV label="Limit" value={run.limit ? `${run.limit} new job${run.limit === 1 ? "" : "s"}` : "none — every match"} />
            <KV
                label="Companies"
                value={`${run.results.length} of ${run.companies}${running ? " so far" : ""}${
                    skipped ? ` · ${skipped} skipped, limit reached` : ""
                }`}
            />
            <KV label="Found" value={describeTotals(totals)} />
            {run.filters ? (
                <>
                    <KV label="Searched for" value={run.filters.titles.join(", ")} />
                    <KV label="In" value={run.filters.locations.join(", ")} />
                </>
            ) : null}
            {run.error ? <p className="text-[12px] text-risk-ink">{run.error}</p> : null}
            {found.length ? (
                <div className="flex flex-wrap gap-1.5 pt-1">
                    {found.map((result) => (
                        <Badge key={result.name} variant="soft">
                            {result.name} · {result.new} new
                        </Badge>
                    ))}
                </div>
            ) : null}
        </>
    );
}

function Recorded({ discovery, loaded }) {
    if (!loaded) return <p className="text-[13px] text-muted-foreground">reading…</p>;
    if (!discovery.companies) return <p className="text-[13px] text-muted-foreground">No run yet.</p>;

    const problems = [
        discovery.blocked ? `${discovery.blocked} blocked by robots.txt` : null,
        discovery.failed ? `${discovery.failed} with errors` : null,
    ].filter(Boolean);

    return (
        <>
            <KV label="Last result recorded" value={when(discovery.lastRunAt)} />
            <KV label="Companies" value={`${discovery.companies} with a result`} />
            <KV
                label="Found"
                value={[`${discovery.newJobs} new job${discovery.newJobs === 1 ? "" : "s"}`, ...problems].join(" · ")}
            />
            <p className="text-[12px] text-muted-foreground">
                Taken from each company&apos;s latest result. The full run details — start time, duration,
                what it searched for — were cleared when the AI tier restarted.
            </p>
        </>
    );
}

function sum(results) {
    return results.reduce(
        (total, result) => ({
            new: total.new + (result.new ?? 0),
            duplicate: total.duplicate + (result.duplicate ?? 0),
            failed: total.failed + (result.failed ?? 0),
            blocked: total.blocked + (result.blocked ? 1 : 0),
        }),
        { new: 0, duplicate: 0, failed: 0, blocked: 0 }
    );
}

function describeTotals(totals) {
    const parts = [`${totals.new} new`, `${totals.duplicate} already stored`];
    if (totals.failed) parts.push(`${totals.failed} failed`);
    if (totals.blocked) parts.push(`${totals.blocked} blocked`);
    return parts.join(" · ");
}

function when(timestamp) {
    return new Date(timestamp).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

function duration(start, end) {
    const seconds = Math.max(0, Math.round(((end ? new Date(end) : new Date()) - new Date(start)) / 1000));
    if (seconds < 60) return `${seconds}s`;
    return `${Math.floor(seconds / 60)} min ${seconds % 60}s`;
}
