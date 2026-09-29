"use client";

import { useState } from "react";

import { cn } from "@/util/helper";

/**
 * An editable token list: type and press Enter (or a comma) to add, × to remove,
 * Backspace in an empty box to drop the last one. Repeats are ignored regardless of
 * case, matching how the server stores them. `onEnterEmpty`, if given, is what Enter
 * does when there is nothing typed to add — a search box submits with it.
 * `suggestions` are offered under the text as you type: names starting with it first,
 * then ones containing it. ↑/↓ move, Enter picks, Escape closes.
 */
function TokenInput({ items, onChange, placeholder, tone = "soft", disabled = false, onEnterEmpty, suggestions }) {
    const [draft, setDraft] = useState("");
    const [active, setActive] = useState(-1);
    const [closed, setClosed] = useState(false);
    const matches = suggest(suggestions, draft, items);
    const open = !closed && matches.length > 0;

    function add(raw) {
        const term = raw.trim();
        setDraft("");
        setActive(-1);
        if (!term || items.some((item) => item.toLowerCase() === term.toLowerCase())) return;
        onChange([...items, term]);
    }

    function onKeyDown(event) {
        if (open && (event.key === "ArrowDown" || event.key === "ArrowUp")) {
            event.preventDefault();
            const step = event.key === "ArrowDown" ? 1 : -1;
            setActive((index) => (index + step + matches.length) % matches.length);
        } else if (open && event.key === "Escape") {
            setClosed(true);
        } else if (open && event.key === "Enter" && active >= 0) {
            event.preventDefault();
            add(matches[active]);
        } else if (event.key === "Enter" && !draft.trim() && onEnterEmpty) {
            event.preventDefault();
            onEnterEmpty();
        } else if (event.key === "Enter" || event.key === ",") {
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
            {/* The list hangs from the text box itself, so it opens where you are typing. */}
            <div className="relative min-w-[140px] grow">
                <input
                    value={draft}
                    disabled={disabled}
                    role={suggestions ? "combobox" : undefined}
                    aria-expanded={suggestions ? open : undefined}
                    onChange={(event) => {
                        setDraft(event.target.value);
                        setActive(-1);
                        setClosed(false);
                    }}
                    onKeyDown={onKeyDown}
                    onBlur={() => add(draft)}
                    placeholder={items.length ? "" : placeholder}
                    className="h-8 w-full bg-transparent px-1.5 text-[14px] outline-none placeholder:text-muted-foreground"
                />
                {open ? (
                    <ul
                        role="listbox"
                        className="absolute top-full left-0 z-30 mt-1.5 max-h-64 w-64 overflow-y-auto rounded-sm border border-border bg-card py-1 shadow-raise"
                    >
                        {matches.map((option, index) => (
                            <li
                                key={option}
                                role="option"
                                aria-selected={index === active}
                                // mousedown, not click: it lands before the input's blur adds the draft.
                                onMouseDown={(event) => {
                                    event.preventDefault();
                                    add(option);
                                }}
                                onMouseEnter={() => setActive(index)}
                                className={cn(
                                    "cursor-pointer px-3 py-2 text-[13.5px]",
                                    index === active ? "bg-primary-tint text-accent-foreground" : "hover:bg-secondary"
                                )}
                            >
                                {option}
                            </li>
                        ))}
                    </ul>
                ) : null}
            </div>
        </div>
    );
}

/** Up to eight suggestions for `draft`: prefix matches first, then the rest, skipping
 * what is already picked. Nothing until something is typed. */
function suggest(suggestions, draft, items) {
    const term = draft.trim().toLowerCase();
    if (!suggestions || !term) return [];
    const picked = new Set(items.map((item) => item.toLowerCase()));
    const open = suggestions.filter((option) => !picked.has(option.toLowerCase()));
    const starts = open.filter((option) => option.toLowerCase().startsWith(term));
    const contains = open.filter((option) => !option.toLowerCase().startsWith(term) && option.toLowerCase().includes(term));
    return [...starts, ...contains].slice(0, 8);
}

export { TokenInput };
