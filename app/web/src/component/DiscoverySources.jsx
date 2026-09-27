"use client";

import { AlertTriangle, Play, RefreshCw } from "lucide-react";

import { useDiscovery } from "@/component/DiscoveryContext";
import { Panel, PanelHeader, PanelTitle } from "@/component/ui/panel";
import { Button } from "@/component/ui/button";
import { Toggle } from "@/component/ui/toggle";
import { Tooltip } from "@/component/ui/tooltip";
import { cn } from "@/util/helper";

/**
 * The Sources rail on Settings: every registered career source with its last result
 * and an on/off switch, and the button that starts a run. State and polling live in
 * `DiscoveryProvider`, shared with the Last run panel.
 */
export function DiscoverySources() {
    const { sources, run, running, error, starting, watching, start, checkAgain, setEnabled } =
        useDiscovery();

    const live = new Map((running ? run.results : []).map((result) => [result.name, result]));
    const enabled = sources?.filter((source) => source.enabled).length ?? 0;

    return (
        <Panel>
            <PanelHeader>
                <PanelTitle>Sources</PanelTitle>
                <span className="grow" />
                <Button size="sm" onClick={start} disabled={running || starting || !enabled}>
                    {running ? <RefreshCw className="animate-spin" /> : <Play />}
                    {running ? "Running…" : "Run discovery"}
                </Button>
            </PanelHeader>

            <p className="border-b border-border px-5 py-3 text-[12.5px] text-muted-foreground">
                {summary(sources, enabled, run)}
            </p>

            {error ? (
                <div className="flex items-start gap-1.5 border-b border-border px-5 py-3 text-[12px] text-risk-ink">
                    <AlertTriangle className="mt-0.5 size-[12px] shrink-0" />
                    <span className="grow">{error}</span>
                    {running && !watching ? (
                        <button type="button" className="shrink-0 underline" onClick={checkAgain}>
                            Check again
                        </button>
                    ) : null}
                </div>
            ) : null}

            <div className="max-h-[420px] overflow-y-auto">
                {(sources ?? []).map((source, i) => (
                    <div
                        key={source.id}
                        className={cn(
                            "flex items-center gap-3 px-5 py-3",
                            i < sources.length - 1 && "border-b border-border"
                        )}
                    >
                        <div className="min-w-0 grow">
                            <p className={cn("truncate text-[14px]", !source.enabled && "text-muted-foreground")}>
                                {source.name}
                            </p>
                            {/* The notes, or the last error, say why — shown only when there are some. */}
                            <Detail note={source.notes ?? source.lastResult?.error}>
                                <p className="mt-0.5 truncate text-[12px] text-muted-foreground">
                                    {describe(source, live, running)}
                                </p>
                            </Detail>
                            {source.enabled && source.lastRunAt && !live.has(source.name) ? (
                                <p className="mt-0.5 text-[11.5px] text-muted-foreground/80">
                                    {ago(source.lastRunAt)}
                                </p>
                            ) : null}
                        </div>
                        {/* A run reads its list when it starts, so a switch flipped mid-run
                            would look like it did something it cannot. */}
                        <Toggle
                            on={source.enabled}
                            disabled={running}
                            label={`${source.enabled ? "Disable" : "Enable"} ${source.name}`}
                            onChange={(value) => setEnabled(source, value)}
                        />
                    </div>
                ))}
            </div>
        </Panel>
    );
}

function summary(sources, enabled, run) {
    if (!sources) return "reading the career sources…";
    if (!sources.length) return "No companies registered yet. Seed them with server/seed_career_sources.py.";

    const base = `${enabled} of ${sources.length} companies enabled`;
    if (!run) return base;
    if (run.status === "running") return `${base} · ${run.results.length} of ${run.companies} done`;
    if (run.status === "failed") return `${base} · last run stopped: ${run.error}`;

    const found = run.results.reduce((total, result) => total + result.new, 0);
    return `${base} · last run found ${found} new job${found === 1 ? "" : "s"}`;
}

function describe(source, live, running) {
    if (!source.enabled) return source.notes ? `disabled — ${source.notes}` : "disabled";

    const result = live.get(source.name) ?? (running ? null : source.lastResult);
    if (!result) return running ? "waiting…" : "not run yet";
    if (result.blocked) return "blocked by robots.txt";
    if (result.error && !result.new && !result.duplicate) return `error — ${result.error}`;

    const parts = [`${result.new} new`, `${result.duplicate} already stored`];
    if (result.failed) parts.push(`${result.failed} failed`);
    return parts.join(" · ");
}

function ago(timestamp) {
    const minutes = Math.round((Date.now() - new Date(timestamp).getTime()) / 60000);
    if (minutes < 1) return "run just now";
    if (minutes < 60) return `run ${minutes} min ago`;
    if (minutes < 60 * 24) return `run ${Math.round(minutes / 60)} h ago`;
    return `run ${new Date(timestamp).toLocaleDateString(undefined, { dateStyle: "medium" })}`;
}

function Detail({ note, children }) {
    return note ? <Tooltip content={note}>{children}</Tooltip> : children;
}
