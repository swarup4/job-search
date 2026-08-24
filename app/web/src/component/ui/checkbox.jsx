"use client";

import { Check } from "lucide-react";
import { cn } from "@/util/cn";

/**
 * Controlled only — no defaultChecked, no internal state. A missing keyword must
 * never arrive pre-checked (FR-2.5); the parent holds a Set that starts empty.
 */
function Checkbox({ className, checked, onCheckedChange, ...props }) {
    return (
        <span
            role="checkbox"
            aria-checked={checked}
            onClick={() => onCheckedChange?.(!checked)}
            className={cn(
                "grid size-[18px] shrink-0 place-items-center rounded-sm border transition-all",
                checked ? "border-primary bg-primary text-primary-foreground" : "border-border bg-card",
                className
            )}
            {...props}
        >
            {checked ? <Check className="size-3 stroke-[3]" /> : null}
        </span>
    );
}

export { Checkbox };
