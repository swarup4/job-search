"use client";

import { useSyncExternalStore } from "react";
import { AlertTriangle, Check, Info, X } from "lucide-react";

import { cn } from "@/util/helper";

/**
 * Transient feedback, app-wide.
 *
 * The store is a module-level list rather than React context, so `toast.error(...)`
 * can be called from anywhere — including a service, or a catch block that is not
 * inside a component — without a provider wrapping the call site. `<Toaster />` is
 * mounted once, in the root layout.
 *
 * Use this for the outcome of something the user just did. A region that has no
 * content to show — a failed initial load — still needs its own message in place,
 * because a toast disappears and leaves an empty screen behind.
 */

// An error is read; a success is glanced at.
const DURATION = { success: 4000, info: 5000, error: 8000 };

const EMPTY = [];
let toasts = EMPTY;
let lastId = 0;
const listeners = new Set();

function set(next) {
    toasts = next;
    listeners.forEach((listener) => listener());
}

function subscribe(listener) {
    listeners.add(listener);
    return () => listeners.delete(listener);
}

function show(tone, message) {
    // Never open an empty toast: callers pass a message that may be undefined.
    if (!message) return null;

    const id = (lastId += 1);
    const timer = setTimeout(() => dismiss(id), DURATION[tone]);
    set([...toasts, { id, tone, message: String(message), timer }]);
    return id;
}

export function dismiss(id) {
    const found = toasts.find((item) => item.id === id);
    if (!found) return;
    clearTimeout(found.timer);
    set(toasts.filter((item) => item.id !== id));
}

export const toast = {
    success: (message) => show("success", message),
    error: (message) => show("error", message),
    info: (message) => show("info", message),
};

const TONE = {
    success: { icon: Check, accent: "bg-primary", ink: "text-primary" },
    error: { icon: AlertTriangle, accent: "bg-risk-solid", ink: "text-risk-ink" },
    info: { icon: Info, accent: "bg-muted-foreground", ink: "text-muted-foreground" },
};

/**
 * Where the stack sits. Every entry is a full literal class string, because Tailwind
 * scans the source for them — a class assembled at runtime is never generated.
 *
 * `stack` is not cosmetic. The container is pinned to one edge, so the newest toast
 * has to render at the far end from that edge; otherwise adding one shunts every
 * toast already on screen.
 *
 * `top-[84px]` clears the 68px sticky Topbar rather than floating over it — the
 * header's own buttons sit in that corner.
 */
const PLACEMENT = {
    "top-left": { y: "top-[84px]", x: "left-5", stack: "flex-col", enter: "down" },
    "top-center": { y: "top-[84px]", x: "left-1/2 -translate-x-1/2", stack: "flex-col", enter: "down" },
    "top-right": { y: "top-[84px]", x: "right-5", stack: "flex-col", enter: "down" },
    "bottom-left": { y: "bottom-5", x: "left-5", stack: "flex-col-reverse", enter: "up" },
    "bottom-center": { y: "bottom-5", x: "left-1/2 -translate-x-1/2", stack: "flex-col-reverse", enter: "up" },
    "bottom-right": { y: "bottom-5", x: "right-5", stack: "flex-col-reverse", enter: "up" },
};

/**
 * @param position one of PLACEMENT's keys. Changing it moves the stack, flips the
 *   order new toasts arrive in, and reverses the direction they slide from — the
 *   three have to agree, so they are decided together here rather than at each site.
 */
export function Toaster({ position = "top-right" }) {
    const items = useSyncExternalStore(subscribe, () => toasts, () => EMPTY);
    const place = PLACEMENT[position] ?? PLACEMENT["top-right"];

    return (
        // Always in the DOM, so a screen reader is already watching the region when
        // the first message lands. `pointer-events-none` keeps the empty stack from
        // covering the corner of the page.
        <div
            aria-live="polite"
            aria-atomic="false"
            className={cn(
                "pointer-events-none fixed z-50 flex w-[min(380px,calc(100vw-40px))] gap-2.5",
                place.y,
                place.x,
                place.stack
            )}
        >
            {items.map((item) => (
                <Toast key={item.id} {...item} enter={place.enter} />
            ))}
        </div>
    );
}

function Toast({ id, tone, message, enter }) {
    const { icon: Icon, accent, ink } = TONE[tone] ?? TONE.info;

    return (
        <div
            data-enter={enter}
            className="toast panel pointer-events-auto relative flex items-start gap-3 overflow-hidden py-3 pl-4 pr-3"
        >
            <span className={cn("absolute inset-y-0 left-0 w-[3px]", accent)} />
            <Icon className={cn("mt-0.5 size-[15px] shrink-0", ink)} />
            <p className="grow text-[13px] leading-relaxed text-pretty">{message}</p>
            <button
                type="button"
                onClick={() => dismiss(id)}
                aria-label="Dismiss"
                className="mt-0.5 shrink-0 text-muted-foreground transition-colors hover:text-foreground"
            >
                <X className="size-[14px]" />
            </button>
        </div>
    );
}
