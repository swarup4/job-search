"use client";

import { useState } from "react";
import { cn } from "@/util/cn";

function Toggle({ defaultOn = false, disabled = false, onChange }) {
    const [on, setOn] = useState(defaultOn);
    return (
        <button
            type="button"
            role="switch"
            aria-checked={on}
            disabled={disabled}
            onClick={() => {
                if (disabled) return;
                setOn(!on);
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
