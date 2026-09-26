"use client";

import { useEffect, useRef, useState } from "react";

import { ApiError } from "@/services";

// Checks start every 3s and stretch to every 10s: a run takes minutes, and its later
// steps do not need second-by-second news.
const POLL_FIRST_MS = 3000;
const POLL_MAX_MS = 10000;
// Consecutive failures before polling stops and waits for a click instead.
const MAX_FAILURES = 3;
// A run still "running" after this long is treated as stuck, not polled forever.
const POLL_GIVE_UP_MS = 30 * 60 * 1000;

/**
 * Follows a background run on the AI tier — discovery, analysis — until it ends.
 *
 * One request at a time, never overlapping, backing off, paused while the tab is
 * hidden, and stopped after repeated failures or half an hour, with `checkAgain` to
 * resume. `fetchRun` answers the latest run or null; `onFinished` is called once
 * when a watched run stops running.
 *
 * `fetchOnMount: false` asks nothing until `watch` hands it a run the user just
 * started — for runs whose results are read from the database anyway, where checking
 * for a run on every page load would be a request with nothing to show for it.
 */
export function usePolledRun(fetchRun, onFinished, { fetchOnMount = true } = {}) {
    const [run, setRun] = useState(null);
    const [error, setError] = useState(null);
    // False once polling has given up; checkAgain turns it back on.
    const [watching, setWatching] = useState(true);
    const loading = useRef(false);
    // A ref so a new callback each render does not restart the polling effect.
    const finished = useRef(onFinished);
    finished.current = onFinished;

    useEffect(() => {
        // A ref, not state: React's development double-mount fires this twice.
        if (!fetchOnMount || loading.current) return;
        loading.current = true;
        fetchRun()
            .then(setRun)
            .catch(() => {
                // The AI tier not running is a normal state here; starting a run says so.
            });
    }, [fetchRun, fetchOnMount]);

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
                const latest = await fetchRun();
                if (cancelled) return;
                failures = 0;
                setRun(latest);
                if (latest?.status !== "running") {
                    finished.current?.();
                    return;
                }
            } catch (failure) {
                if (cancelled) return;
                failures += 1;
                if (failures >= MAX_FAILURES) {
                    giveUp(failure instanceof ApiError ? failure.message : "Lost contact with the run.");
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
    }, [running, watching, fetchRun]);

    /** Start following a run the caller just started. */
    function watch(started) {
        setError(null);
        setRun(started);
        setWatching(true);
    }

    function checkAgain() {
        setError(null);
        setWatching(true);
    }

    return { run, running, error, setError, watching, watch, checkAgain };
}
