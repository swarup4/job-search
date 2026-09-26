"use client";

import { useState } from "react";
import { Bookmark } from "lucide-react";
import { cn } from "@/util/helper";

/**
 * Toggles a job on and off the shortlist. With `onToggle` the change is saved: the
 * button moves first and snaps back if the save is refused. Without it the state is
 * local only — the screens still on fixtures use it that way.
 */
export function ShortlistButton({ shortlisted = false, size = "md", className, onToggle }) {
  const [on, setOn] = useState(shortlisted);
  const [saving, setSaving] = useState(false);
  const iconOnly = size === "sm";

  return (
    <button
      type="button"
      aria-pressed={on}
      aria-label={on ? "Remove from shortlist" : "Add to shortlist"}
      title={on ? "Remove from shortlist" : "Add to shortlist"}
      disabled={saving}
      onClick={async (e) => {
        // these sit inside link rows — don't navigate when toggling
        e.preventDefault();
        e.stopPropagation();
        const next = !on;
        setOn(next);
        if (!onToggle) return;
        setSaving(true);
        try {
          await onToggle(next);
        } catch {
          setOn(!next);
        } finally {
          setSaving(false);
        }
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
