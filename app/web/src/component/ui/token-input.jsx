"use client";

import { useState } from "react";

import { cn } from "@/util/helper";

/**
 * An editable token list: type and press Enter (or a comma) to add, × to remove,
 * Backspace in an empty box to drop the last one. Repeats are ignored regardless of
 * case, matching how the server stores them.
 */
function TokenInput({ items, onChange, placeholder, tone = "soft", disabled = false }) {
    const [draft, setDraft] = useState("");

    function add(raw) {
        const term = raw.trim();
        setDraft("");
        if (!term || items.some((item) => item.toLowerCase() === term.toLowerCase())) return;
        onChange([...items, term]);
    }

    function onKeyDown(event) {
        if (event.key === "Enter" || event.key === ",") {
            event.preventDefault();
            add(draft);
        } else if (event.key === "Backspace" && !draft && items.length) {
            onChange(items.slice(0, -1));
        }
    }

    return (
        <div
            className={cn(
                "flex min-h-11 flex-wrap items-center gap-2 rounded-sm border border-input bg-card px-2 py-1.5 focus-within:border-primary",
                disabled && "opacity-60"
            )}
        >
            {items.map((item) => (
                <span
                    key={item}
                    className={cn(
                        "inline-flex items-center gap-2 rounded-sm px-2.5 py-1 text-[13px]",
                        tone === "soft"
                            ? "bg-primary-tint text-accent-foreground"
                            : "bg-secondary text-muted-foreground"
                    )}
                >
                    {item}
                    <button
                        type="button"
                        aria-label={`Remove ${item}`}
                        disabled={disabled}
                        onClick={() => onChange(items.filter((other) => other !== item))}
                        className="text-[15px] leading-none opacity-45 hover:opacity-100"
                    >
                        ×
                    </button>
                </span>
            ))}
            <input
                value={draft}
                disabled={disabled}
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={onKeyDown}
                onBlur={() => add(draft)}
                placeholder={items.length ? "" : placeholder}
                className="h-8 min-w-[140px] grow bg-transparent px-1.5 text-[14px] outline-none placeholder:text-muted-foreground"
            />
        </div>
    );
}

export { TokenInput };
