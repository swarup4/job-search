"use client";

import { useState } from "react";
import { cn } from "@/util/helper";

/** Uncontrolled by default; pass `on` to drive it from outside, e.g. to snap back
 * when a save fails. */
function Toggle({ on: controlled, defaultOn = false, disabled = false, onChange, label }) {
    const [inner, setInner] = useState(defaultOn);
    const on = controlled ?? inner;
    return (
        <button
            type="button"
            role="switch"
            aria-checked={on}
            aria-label={label}
            disabled={disabled}
            onClick={() => {
                if (disabled) return;
                setInner(!on);
                onChange?.(!on);
            }}
            className={cn(
                "relative h-[22px] w-[38px] shrink-0 rounded-pill transition-colors",
                on ? "bg-primary" : "bg-border",
                disabled && "cursor-not-allowed opacity-50"
            )}
        >
            <span
                className={cn(
                    "absolute top-[3px] size-4 rounded-full bg-white transition-all",
                    on ? "left-[19px]" : "left-[3px]"
                )}
            />
        </button>
    );
}

export { Toggle };
