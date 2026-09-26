"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";

import { ApiError, getDiscoveryRun, listCareerSources, startDiscovery, updateCareerSource } from "@/services";
import { usePolledRun } from "@/hooks/usePolledRun";

const DiscoveryContext = createContext(null);

/**
 * One copy of the career sources and the current run for the whole Settings page,
 * so the Sources rail and the Last run panel read the same state and poll once.
 * When a run ends the sources are re-read, since every company's result is also
 * stored on its source.
 */
export function DiscoveryProvider({ children }) {
    const [sources, setSources] = useState(null);
    const [starting, setStarting] = useState(false);
    const loading = useRef(false);

    // When a run ends, re-read the sources: every company's result is stored on it.
    const poll = usePolledRun(getDiscoveryRun, () => loadSources());
    const { setError } = poll;

    const loadSources = useCallback(async () => {
        try {
            setSources(await listCareerSources());
        } catch (failure) {
            setError(messageOf(failure, "Could not read the career sources."));
        }
    }, [setError]);

    useEffect(() => {
        // A ref, not state: React's development double-mount fires this twice.
        if (loading.current) return;
        loading.current = true;
        loadSources();
    }, [loadSources]);

    async function start() {
        setStarting(true);
        poll.setError(null);
        try {
            poll.watch(await startDiscovery());
        } catch (failure) {
            poll.setError(messageOf(failure, "Could not start a discovery run."));
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
