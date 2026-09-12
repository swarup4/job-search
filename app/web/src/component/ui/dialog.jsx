"use client";

import { useEffect, useRef } from "react";
import { X } from "lucide-react";
import { cn } from "@/util/helper";

function Dialog({ open, onClose, title, description, children, className }) {
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
