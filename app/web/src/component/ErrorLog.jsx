"use client";

import { useCallback, useEffect, useState } from "react";
import { Bug, Loader2, RefreshCw, Trash2 } from "lucide-react";

import { ApiError, clearErrorLog, getErrorLog } from "@/services";
import { Badge } from "@/component/ui/badge";
import { Button } from "@/component/ui/button";
import { Dialog } from "@/component/ui/dialog";
import { toast } from "@/component/ui/toast";

const SOURCE_LABEL = { server: "API server", ai: "AI tier", web: "Dashboard" };

/**
 * The header's error-log button and the drawer it opens: every tier's errors, read
 * from the one file the server and the AI tier append to — the dashboard's own
 * failures reach it through the server.
 */
export function ErrorLogButton() {
    const [open, setOpen] = useState(false);
    const [entries, setEntries] = useState(null);
    const [loadError, setLoadError] = useState(null);
    const [loading, setLoading] = useState(false);
    const [clearing, setClearing] = useState(false);

    const load = useCallback(async () => {
        setLoading(true);
        try {
            setEntries(await getErrorLog());
            setLoadError(null);
        } catch (failure) {
            setLoadError(failure instanceof ApiError ? failure.message : "Could not read the error log.");
        } finally {
            setLoading(false);
        }
    }, []);

    // Once for the badge; again on every open, since errors land while it is shut.
    useEffect(() => {
        load();
    }, [load]);

    function show() {
        setOpen(true);
        load();
    }

    async function clear() {
        if (!window.confirm("Delete every entry in the error log?")) return;
        setClearing(true);
        try {
            await clearErrorLog();
            setEntries([]);
        } catch (failure) {
            toast.error(failure instanceof ApiError ? failure.message : "Could not clear the error log.");
        } finally {
            setClearing(false);
        }
    }

    const count = entries?.length ?? 0;

    return (
        <>
            <button
                type="button"
                onClick={show}
                aria-label={count ? `Error log, ${count} entries` : "Error log"}
                title="Error log"
                className="relative grid size-10 place-items-center rounded-pill hover:bg-secondary"
            >
                <Bug className="size-[17px] text-muted-foreground" />
                {count > 0 ? (
                    <span className="absolute right-1 top-1 grid h-[17px] min-w-[17px] place-items-center rounded-full bg-risk-solid px-1 text-[10px] font-bold text-white">
                        {count > 99 ? "99+" : count}
                    </span>
                ) : null}
            </button>

            <Dialog
                open={open}
                onClose={() => setOpen(false)}
                title="Error log"
                description="Failures from the API server, the AI tier and this dashboard, newest first."
                className="drawer"
            >
                <div className="flex items-center gap-2 border-b border-border px-5 py-3">
                    <span className="text-[12.5px] text-muted-foreground">
                        {count} {count === 1 ? "entry" : "entries"}
                    </span>
                    <span className="grow" />
                    <Button variant="outline" size="sm" onClick={load} disabled={loading}>
                        {loading ? <Loader2 className="animate-spin" /> : <RefreshCw />}
                        Refresh
                    </Button>
                    <Button variant="outline" size="sm" onClick={clear} disabled={clearing || !count}>
                        {clearing ? <Loader2 className="animate-spin" /> : <Trash2 />}
                        Clear
                    </Button>
                </div>

                <div className="min-h-0 flex-1 overflow-y-auto">
                    {loadError ? (
                        <p className="px-5 py-6 text-[13px] text-risk-ink">{loadError}</p>
                    ) : entries === null ? (
                        <p className="flex items-center gap-2 px-5 py-6 text-[13px] text-muted-foreground">
                            <Loader2 className="size-4 animate-spin" />
                            Reading the log…
                        </p>
                    ) : count === 0 ? (
                        <p className="px-5 py-6 text-[13px] text-muted-foreground">No errors logged.</p>
                    ) : (
                        <ul className="divide-y divide-border">
                            {entries.map((entry) => (
                                <Entry key={entry.id} entry={entry} />
                            ))}
                        </ul>
                    )}
                </div>
            </Dialog>
        </>
    );
}

function Entry({ entry }) {
    const context = Object.entries(entry.context ?? {})
        .filter(([, value]) => value !== null && value !== "")
        .map(([key, value]) => `${key}: ${value}`)
        .join(" · ");

    return (
        <li className="px-5 py-3">
            <div className="flex flex-wrap items-center gap-2">
                <Badge variant="muted">{SOURCE_LABEL[entry.source] ?? entry.source}</Badge>
                {entry.level !== "error" && <Badge variant="attention">{entry.level}</Badge>}
                <span className="grow" />
                <time dateTime={entry.at} className="text-[12px] text-muted-foreground">
                    {new Date(entry.at).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "medium" })}
                </time>
            </div>
            <p className="mt-1.5 break-words text-[13px] text-foreground">{entry.message}</p>
            {context && (
                <p className="mt-1 break-all font-mono text-[11.5px] text-muted-foreground">{context}</p>
            )}
            {entry.detail && (
                <details className="mt-1.5">
                    <summary className="cursor-pointer text-[12px] text-muted-foreground hover:text-foreground">
                        Details
                    </summary>
                    <pre className="mt-1.5 max-h-[240px] overflow-auto rounded-sm bg-secondary p-3 font-mono text-[11.5px] leading-relaxed whitespace-pre text-muted-foreground">
                        {entry.detail}
                    </pre>
                </details>
            )}
        </li>
    );
}
