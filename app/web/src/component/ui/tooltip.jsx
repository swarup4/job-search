"use client";

import { useId, useRef, useState } from "react";

import { cn } from "@/util/helper";

/**
 * A hover tooltip, for text a layout has to cut short. With `onlyWhenTruncated` it
 * measures its child when the pointer arrives and stays shut if the text already
 * fits — a tooltip repeating what is fully on screen is noise.
 *
 * Mouse only by design: `truncate` clips visually, so assistive tech already reads
 * the full text from the DOM, and a keyboard user focusing the surrounding link
 * hears it too. `align="end"` opens the bubble leftwards from the trigger's right
 * edge, for something sitting at the right of its container.
 */
function Tooltip({ content, children, onlyWhenTruncated = false, align = "start", className }) {
    const [open, setOpen] = useState(false);
    const wrapper = useRef(null);
    const id = useId();

    function show() {
        const target = wrapper.current?.firstElementChild;
        if (onlyWhenTruncated && target && target.scrollWidth <= target.clientWidth) return;
        setOpen(true);
    }

    return (
        <div
            ref={wrapper}
            className={cn("relative min-w-0", className)}
            onMouseEnter={show}
            onMouseLeave={() => setOpen(false)}
            aria-describedby={open ? id : undefined}
        >
            {children}
            {open ? (
                <span
                    id={id}
                    role="tooltip"
                    className={cn(
                        "pointer-events-none absolute bottom-full z-30 mb-2 w-max max-w-[280px] whitespace-normal rounded-sm bg-foreground px-2.5 py-1.5 text-[12.5px] font-normal leading-snug text-background shadow-raise",
                        align === "end" ? "right-0" : "left-0"
                    )}
                >
                    {content}
                    {/* The arrow: a square turned 45°, half tucked under the bubble so only
                        its lower point shows, aimed at the start of the text. */}
                    <span
                        aria-hidden="true"
                        className={cn(
                            "absolute top-full size-2 -translate-y-1/2 rotate-45 bg-foreground",
                            align === "end" ? "right-3" : "left-3"
                        )}
                    />
                </span>
            ) : null}
        </div>
    );
}

export { Tooltip };
