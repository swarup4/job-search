"use client";

import { LayoutGrid, List } from "lucide-react";
import { cn } from "@/util/cn";

export function ViewToggle({ view, onChange }) {
  return (
    <div className="flex items-center gap-1 rounded-pill bg-secondary p-1">
      {[["list", List], ["grid", LayoutGrid]].map(([key, Icon]) => (
        <button
          key={key}
          type="button"
          aria-label={`${key} view`}
          onClick={() => onChange(key)}
          className={cn(
            "grid size-8 place-items-center rounded-pill transition-colors",
            view === key ? "bg-card text-primary shadow-soft" : "text-muted-foreground"
          )}
        >
          <Icon className="size-[15px]" />
        </button>
      ))}
    </div>
  );
}
