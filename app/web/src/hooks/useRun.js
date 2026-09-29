"use client";

import { useEffect, useRef, useState } from "react";

import { ApiError, followRun, startRun } from "@/services";

// Events that are one finished item of the run, collected into `run.results`.
const RESULT_EVENTS = new Set(["job_done", "company_done"]);

/**
 * One background run on the AI tier — `discovery`, `analysis` or `scoring` — started or
 * joined, and followed over its event stream until `run_done`.
 *
 * The stream is also how a page finds your latest run: it replays from `run_started`,
 * which carries the run, and marks what had already happened as `replay`. A page that
 * joins (`attachOnMount`, or a start that answers a run already going) shows replayed
 * events without announcing them; a page that started the run announces everything.
 *
 * `onEvent(event, { replay })` sees every event; `onFinished` runs once, when the run
 * ends while this page is watching.
 */
export function useRun(kind, { onEvent, onFinished, attachOnMount = false } = {}) {
    const [run, setRun] = useState(null);
    const [error, setError] = useState(null);
    const [watching, setWatching] = useState(true);
    // Refs, not state: the stream's handlers outlive the render that created them.
    const handlers = useRef({ onEvent, onFinished });
    handlers.current = { onEvent, onFinished };
    const stream = useRef(null);
    const lastId = useRef(null);
    const ended = useRef(false);
    const joining = useRef(false);
    const mounted = useRef(false);

    useEffect(() => () => stream.current?.abort(), []);

    useEffect(() => {
        // A ref, not state: React's development double-mount fires this twice.
        if (!attachOnMount || mounted.current) return;
        mounted.current = true;
        follow({ join: true, quietIfMissing: true });
        // Asked once per mount; `kind` never changes for a page.
    }, [kind, attachOnMount]);

    function apply(event) {
        const replay = joining.current && event.replay;
        if (event.type === "run_started") setRun(event.run);
        else if (RESULT_EVENTS.has(event.type)) {
            setRun((prev) =>
                prev
                    ? {
                          ...prev,
                          results: [...prev.results, event],
                          ...(event.scored != null ? { scored: event.scored, failed: event.failed } : {}),
                      }
                    : prev
            );
        } else if (event.type === "run_done") {
            ended.current = true;
            setRun((prev) =>
                prev ? { ...prev, status: event.status, error: event.error, finishedAt: event.finishedAt } : prev
            );
        }
        handlers.current.onEvent?.(event, { replay });
        if (event.type === "run_done" && !replay) handlers.current.onFinished?.(event);
    }

    async function follow({ join = false, quietIfMissing = false, resume = false } = {}) {
        stream.current?.abort();
        const controller = new AbortController();
        stream.current = controller;
        if (!resume) {
            joining.current = join;
            lastId.current = null;
            ended.current = false;
        }
        setWatching(true);
        try {
            await followRun(kind, {
                onEvent: (event, id) => {
                    lastId.current = id;
                    apply(event);
                },
                lastEventId: lastId.current,
                signal: controller.signal,
            });
            // The stream closed without saying the run ended — the AI tier restarted.
            if (!ended.current && !controller.signal.aborted) {
                setError("Lost the run's progress.");
                setWatching(false);
            }
        } catch (failure) {
            if (controller.signal.aborted) return;
            // No run of yours yet: nothing to show, which is not an error on page load.
            if (quietIfMissing && failure instanceof ApiError && failure.status === 404) return;
            setError(failure instanceof ApiError ? failure.message : "Lost the run's progress.");
            setWatching(false);
        }
    }

    /** Start a run — or join yours when one is already going. Resolves to `{ run }`, or
     * `{ error }` when it could not start (also kept in `error` for the page to show). */
    async function start(body) {
        setError(null);
        try {
            const started = await startRun(kind, body);
            setRun(started);
            // Progress already made means this run was going before the click.
            follow({ join: (started.results?.length ?? 0) > 0 });
            return { run: started };
        } catch (failure) {
            const message = failure instanceof ApiError ? failure.message : "Could not start the run.";
            setError(message);
            return { error: message };
        }
    }

    function checkAgain() {
        setError(null);
        follow({ resume: true });
    }

    const running = run?.status === "running";
    return { run, running, error, setError, watching, start, checkAgain };
}
