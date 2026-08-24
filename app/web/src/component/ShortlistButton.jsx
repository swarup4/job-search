"use client";

import { useState } from "react";
import { Bookmark } from "lucide-react";
import { cn } from "@/util/cn";

/**
 * Toggles a job on and off the shortlist. State is local for now — there is no
 * server yet, so a reload resets it. Swap useState for a POST when `server` lands.
 */
export function ShortlistButton({ shortlisted = false, size = "md", className }) {
  const [on, setOn] = useState(shortlisted);
  const iconOnly = size === "sm";

  return (
    <button
      type="button"
      aria-pressed={on}
      aria-label={on ? "Remove from shortlist" : "Add to shortlist"}
      title={on ? "Remove from shortlist" : "Add to shortlist"}
      onClick={(e) => {
        // these sit inside link rows — don't navigate when toggling
        e.preventDefault();
        e.stopPropagation();
        setOn(!on);
      }}
      className={cn(
        "inline-flex shrink-0 items-center justify-center gap-1.5 rounded-pill border transition-colors",
        iconOnly ? "size-8" : "h-9 px-3.5 text-[13px] font-medium",
        on
          ? "border-primary bg-primary-tint text-primary hover:bg-primary hover:text-primary-foreground"
          : "border-border bg-card text-muted-foreground hover:border-primary hover:text-primary",
        className
      )}
    >
      <Bookmark className={cn(iconOnly ? "size-4" : "size-[15px]", on && "fill-current")} />
      {iconOnly ? null : on ? "Shortlisted" : "Shortlist"}
    </button>
  );
}
