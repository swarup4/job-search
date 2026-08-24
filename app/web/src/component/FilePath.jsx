"use client";

import { useState } from "react";
import { Check, Copy } from "lucide-react";
import { cn } from "@/util/cn";

/** Copyable, not attachable: browsers do not let an extension set a file input (FR-5.5). */
export function FilePath({ path, className }) {
    const [copied, setCopied] = useState(false);

    const copy = async () => {
        try {
            await navigator.clipboard.writeText(path);
            setCopied(true);
            setTimeout(() => setCopied(false), 1400);
        } catch {
            setCopied(false);
        }
    };

    return (
        <button
            type="button"
            onClick={copy}
            className={cn(
                "group inline-flex max-w-full items-center gap-2.5 rounded-sm border border-border bg-well px-3 py-2 transition-colors hover:border-primary",
                className
            )}
        >
            <span className="truncate font-mono text-[12px]">{path}</span>
            <span className="inline-flex shrink-0 items-center gap-1 text-[12px] text-muted-foreground group-hover:text-primary">
                {copied ? <Check className="size-[12px]" /> : <Copy className="size-[12px]" />}
                {copied ? "copied" : "copy"}
            </span>
        </button>
    );
}
