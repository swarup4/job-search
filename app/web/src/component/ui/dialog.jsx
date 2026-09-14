"use client";

import { useEffect, useRef } from "react";
import { X } from "lucide-react";
import { cn } from "@/util/helper";

/**
 * `bare` drops the header row so the content runs edge to edge, and floats the close
 * button over it instead. `title` is still required in that mode — it stops being the
 * visible heading but remains the dialog's accessible name.
 */
function Dialog({ open, onClose, title, description, children, className, bare = false }) {
    const ref = useRef(null);
    const pressedBackdrop = useRef(false);

    useEffect(() => {
        const el = ref.current;
        if (!el) return;
        if (open && !el.open) el.showModal();
        else if (!open && el.open) el.close();
    }, [open]);

    useEffect(() => {
        if (!open) return undefined;
        const previous = document.body.style.overflow;
        document.body.style.overflow = "hidden";
        return () => {
            document.body.style.overflow = previous;
        };
    }, [open]);

    return (
        <dialog
            ref={ref}
            className={cn("dialog", className)}
            aria-label={title}
            onCancel={(event) => {
                event.preventDefault();
                onClose();
            }}
            onMouseDown={(event) => {
                const box = ref.current.getBoundingClientRect();
                pressedBackdrop.current =
                    event.clientX < box.left ||
                    event.clientX > box.right ||
                    event.clientY < box.top ||
                    event.clientY > box.bottom;
            }}
            onClick={(event) => {
                if (event.target === ref.current && pressedBackdrop.current) onClose();
            }}
        >
            {bare ? (
                // Zero-height so it reserves no space, sticky so it stays put while
                // the content scrolls under it.
                <div className="sticky top-0 z-10 h-0">
                    <button
                        type="button"
                        onClick={onClose}
                        aria-label="Close"
                        className="absolute right-3 top-3 grid size-8 place-items-center rounded-pill border border-border bg-card text-muted-foreground shadow-card transition-colors hover:bg-secondary hover:text-foreground"
                    >
                        <X className="size-[15px]" />
                    </button>
                </div>
            ) : (
                <div className="flex items-start gap-3 border-b border-border px-5 py-4">
                    <div className="min-w-0">
                        <h2 className="widget-title">{title}</h2>
                        {description ? (
                            <p className="mt-1 text-[12.5px] leading-relaxed text-muted-foreground">
                                {description}
                            </p>
                        ) : null}
                    </div>
                    <span className="grow" />
                    <button
                        type="button"
                        onClick={onClose}
                        aria-label="Close"
                        className="-mr-1.5 grid size-8 shrink-0 place-items-center rounded-sm text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
                    >
                        <X className="size-[15px]" />
                    </button>
                </div>
            )}
            {children}
        </dialog>
    );
}

function DialogBody({ className, ...props }) {
    return <div className={cn("px-5 py-5", className)} {...props} />;
}

function DialogFooter({ className, ...props }) {
    return (
        <div
            className={cn(
                "flex flex-wrap items-center justify-end gap-3 border-t border-border px-5 py-4",
                className
            )}
            {...props}
        />
    );
}

export { Dialog, DialogBody, DialogFooter };
