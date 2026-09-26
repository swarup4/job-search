"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";

import {
    ApiError,
    getDiscoveryRun,
    listCareerSources,
    startDiscovery,
    updateCareerSource,
} from "@/services";

// Checks start every 3s and stretch to every 10s: a run takes minutes, and its
// later companies do not need second-by-second news.
const POLL_FIRST_MS = 3000;
const POLL_MAX_MS = 10000;
// Consecutive failures before polling stops and waits for a click instead.
const MAX_FAILURES = 3;
// A run still "running" after this long is treated as stuck, not polled forever.
const POLL_GIVE_UP_MS = 30 * 60 * 1000;

const DiscoveryContext = createContext(null);

/**
 * One copy of the career sources and the current run for the whole Settings page,
 * so the Sources rail and the Last run panel read the same state and poll once.
 *
 * A run takes minutes, so the AI tier answers at once and this polls it — one
 * request at a time, never overlapping, backing off, paused while the tab is hidden,
 * and stopped after repeated failures or half an hour. When the run ends the sources
 * are re-read, since every company's result is also stored on its source.
 */
export function DiscoveryProvider({ children }) {
    const [sources, setSources] = useState(null);
    const [run, setRun] = useState(null);
    const [error, setError] = useState(null);
    const [starting, setStarting] = useState(false);
    // False once polling has given up; "Check again" turns it back on.
    const [watching, setWatching] = useState(true);
    const loading = useRef(false);

    const loadSources = useCallback(async () => {
        try {
            setSources(await listCareerSources());
        } catch (failure) {
            setError(messageOf(failure, "Could not read the career sources."));
        }
    }, []);

    useEffect(() => {
        // A ref, not state: React's development double-mount fires this twice.
        if (loading.current) return;
        loading.current = true;
        loadSources();
        getDiscoveryRun()
            .then(setRun)
            .catch(() => {
                // The AI tier not running is a normal state here; Run says so if pressed.
            });
    }, [loadSources]);

    const running = run?.status === "running";

    useEffect(() => {
        if (!running || !watching) return undefined;

        let cancelled = false;
        let timer = null;
        let delay = POLL_FIRST_MS;
        let failures = 0;
        const startedAt = Date.now();

        // setTimeout after each answer rather than setInterval: a slow answer then
        // delays the next check instead of stacking requests behind it.
        function schedule() {
            timer = document.visibilityState === "visible" ? setTimeout(check, delay) : null;
        }

        function giveUp(message) {
            setWatching(false);
            setError(message);
        }

        async function check() {
            timer = null;
            try {
                const latest = await getDiscoveryRun();
                if (cancelled) return;
                failures = 0;
                setRun(latest);
                if (latest?.status !== "running") {
                    loadSources();
                    return;
                }
            } catch (failure) {
                if (cancelled) return;
                failures += 1;
                if (failures >= MAX_FAILURES) {
                    giveUp(messageOf(failure, "Lost contact with the discovery run."));
                    return;
                }
            }
            if (Date.now() - startedAt > POLL_GIVE_UP_MS) {
                giveUp("The run has been going for over 30 minutes; stopped checking.");
                return;
            }
            delay = Math.min(delay * 1.5, POLL_MAX_MS);
            schedule();
        }

        // A hidden tab schedules nothing; coming back checks straight away.
        function onVisibility() {
            if (document.visibilityState === "visible" && timer === null && !cancelled) check();
        }

        schedule();
        document.addEventListener("visibilitychange", onVisibility);
        return () => {
            cancelled = true;
            clearTimeout(timer);
            document.removeEventListener("visibilitychange", onVisibility);
        };
    }, [running, watching, loadSources]);

    function checkAgain() {
        setError(null);
        setWatching(true);
    }

    async function start() {
        setStarting(true);
        setError(null);
        try {
            setRun(await startDiscovery());
            setWatching(true);
        } catch (failure) {
            setError(messageOf(failure, "Could not start a discovery run."));
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
            setError(messageOf(failure, `Could not ${enabled ? "enable" : "disable"} ${source.name}.`));
        }
    }

    const value = { sources, run, running, error, starting, watching, start, checkAgain, setEnabled };
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
