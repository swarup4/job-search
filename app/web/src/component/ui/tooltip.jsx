"use client";

import { useId, useRef, useState } from "react";

import { cn } from "@/util/helper";

/**
 * The one hover tooltip the app uses — never the browser's native `title`, which looks
 * different everywhere. With `onlyWhenTruncated` it measures its child when the pointer
 * arrives and stays shut if the text already fits — cut short by `truncate` (width) or
 * `line-clamp` (height) — since a tooltip repeating what is fully on screen is noise.
 *
 * Mouse only by design: `truncate` clips visually, so assistive tech already reads
 * the full text from the DOM, and a keyboard user focusing the surrounding link
 * hears it too. `align="end"` opens the bubble leftwards from the trigger's right
 * edge, for something sitting at the right of its container; `side="bottom"` opens it
 * below, for something at the top of the page.
 */
function Tooltip({ content, children, onlyWhenTruncated = false, align = "start", side = "top", className }) {
    const [open, setOpen] = useState(false);
    const wrapper = useRef(null);
    const id = useId();

    function show() {
        const target = wrapper.current?.firstElementChild;
        const fits =
            target && target.scrollWidth <= target.clientWidth && target.scrollHeight <= target.clientHeight;
        if (onlyWhenTruncated && fits) return;
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
                        "pointer-events-none absolute z-30 w-max max-w-[280px] whitespace-normal rounded-sm bg-foreground px-2.5 py-1.5 text-[12.5px] font-normal leading-snug text-background shadow-raise",
                        side === "bottom" ? "top-full mt-2" : "bottom-full mb-2",
                        align === "end" ? "right-0" : "left-0"
                    )}
                >
                    {content}
                    {/* The arrow: a square turned 45°, half tucked under the bubble so only
                        its outer point shows, aimed at the start of the text. */}
                    <span
                        aria-hidden="true"
                        className={cn(
                            "absolute size-2 rotate-45 bg-foreground",
                            side === "bottom" ? "bottom-full translate-y-1/2" : "top-full -translate-y-1/2",
                            align === "end" ? "right-3" : "left-3"
                        )}
                    />
                </span>
            ) : null}
        </div>
    );
}

export { Tooltip };
