import { useCallback, useEffect, useRef } from "react";

export const DEBOUNCE_MS = 2000;

/**
 * Defers work until the caller stops producing it — for text inputs, where doing
 * it per keystroke is waste. The input must hold its own value meanwhile, or the
 * pause is visible in the field itself.
 *
 * `schedule(key, fn)` queues; a second call on the same key replaces the pending
 * one rather than queuing both, so switching between fields never drops an edit.
 * `flush()` runs everything pending at once, and must be called before any read
 * of the deferred result that has to be current — a save.
 */
export function useDebounce(wait = DEBOUNCE_MS) {
    const pending = useRef(new Map());
    const timer = useRef(null);

    const flush = useCallback(() => {
        if (timer.current) {
            clearTimeout(timer.current);
            timer.current = null;
        }
        // Copied first: a callback that schedules again must not mutate this loop.
        const queued = [...pending.current.values()];
        pending.current.clear();
        for (const fn of queued) fn();
    }, []);

    const schedule = useCallback(
        (key, fn) => {
            pending.current.set(key, fn);
            if (timer.current) clearTimeout(timer.current);
            timer.current = setTimeout(flush, wait);
        },
        [flush, wait]
    );

    // Unmounting mid-pause must not drop the last few characters.
    useEffect(() => flush, [flush]);

    return { schedule, flush };
}
