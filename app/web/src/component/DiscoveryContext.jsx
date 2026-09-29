"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";

import { ApiError, listCareerSources, updateCareerSource } from "@/services";
import { useRun } from "@/hooks/useRun";
import { useRefreshStatus } from "@/hooks/useStatus";
import { toast } from "@/component/ui/toast";

const DiscoveryContext = createContext(null);

/**
 * One copy of the career sources and the current run for the whole Settings page,
 * so the Sources rail and the Last run panel read the same state and follow one
 * stream. When a run ends the sources are re-read, since every company's result is
 * also stored on its source.
 */
export function DiscoveryProvider({ children }) {
    const [sources, setSources] = useState(null);
    const [starting, setStarting] = useState(false);
    const loading = useRef(false);
    const refreshStatus = useRefreshStatus();
    // loadSources reports into the run's error line, which exists only after useRun.
    const reportError = useRef(() => {});

    const loadSources = useCallback(async () => {
        try {
            setSources(await listCareerSources());
        } catch (failure) {
            reportError.current(messageOf(failure, "Could not read the career sources."));
        }
    }, []);

    // Followed only once you press Run discovery; until then the Last run panel shows
    // the stored summary from the status store, and a second press rejoins a run going.
    const poll = useRun("discovery", {
        onFinished: ({ status, error, new: found, limit }) => {
            if (status === "failed") toast.error(error ?? "Discovery stopped.");
            else
                toast.success(
                    `Discovery finished — ${found} new job${found === 1 ? "" : "s"}${limit ? ` (limit ${limit})` : ""}.`
                );
            loadSources();
            refreshStatus();
        },
    });
    reportError.current = poll.setError;

    useEffect(() => {
        // A ref, not state: React's development double-mount fires this twice.
        if (loading.current) return;
        loading.current = true;
        loadSources();
    }, [loadSources]);

    /** `limit`: stop once that many new jobs are stored; omitted, scrape everything. */
    async function start(limit) {
        setStarting(true);
        try {
            await poll.start(limit ? { limit } : undefined);
        } finally {
            setStarting(false);
        }
    }

    /** Saved at once — there is no Save button for these. The switch moves first and
     * snaps back if the server refuses, so it never shows a state that is not stored. */
    async function setEnabled(source, enabled) {
        const put = (value) =>
            setSources((rows) => rows.map((row) => (row.id === source.id ? { ...row, enabled: value } : row)));
        put(enabled);
        try {
            await updateCareerSource(source.id, { enabled });
        } catch (failure) {
            put(!enabled);
            poll.setError(messageOf(failure, `Could not ${enabled ? "enable" : "disable"} ${source.name}.`));
        }
    }

    const value = {
        sources,
        run: poll.run,
        running: poll.running,
        error: poll.error,
        starting,
        watching: poll.watching,
        start,
        checkAgain: poll.checkAgain,
        setEnabled,
    };
    return <DiscoveryContext.Provider value={value}>{children}</DiscoveryContext.Provider>;
}

export function useDiscovery() {
    const value = useContext(DiscoveryContext);
    if (!value) throw new Error("useDiscovery needs a DiscoveryProvider above it");
    return value;
}

function messageOf(failure, fallback) {
    return failure instanceof ApiError ? failure.message : fallback;
}
