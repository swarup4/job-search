import { cn } from "@/util/cn";

// `label` and `hint` are optional: an unlabelled field (a summary textarea, a links
// row) would otherwise reserve a blank label line and inherit the gap above it.
// `error` replaces the hint rather than stacking under it, so the field does not
// grow a line and shove the form down the moment validation fires.
function Field({ label, hint, error, children, className }) {
    return (
        <label className={cn("flex flex-col gap-2", className)}>
            {label ? <span className="text-[13px] font-medium">{label}</span> : null}
            {children}
            {error ? (
                <span className="text-[12px] text-risk-muted">{error}</span>
            ) : hint ? (
                <span className="text-[12px] text-muted-foreground">{hint}</span>
            ) : null}
        </label>
    );
}

function Input({ className, invalid, ...props }) {
    return (
        <input
            className={cn(
                "h-11 w-full rounded-sm border border-input bg-card px-3.5 text-[14px] outline-none transition-colors placeholder:text-muted-foreground focus:border-primary",
                invalid && "border-risk-rule focus:border-risk-solid",
                className
            )}
            {...props}
        />
    );
}

function Textarea({ className, invalid, ...props }) {
    return (
        <textarea
            className={cn(
                "min-h-[104px] w-full resize-y rounded-sm border border-input bg-card px-3.5 py-2.5 text-[14px] leading-relaxed outline-none transition-colors placeholder:text-muted-foreground focus:border-primary",
                invalid && "border-risk-rule focus:border-risk-solid",
                className
            )}
            {...props}
        />
    );
}

/** Removable token — the reference's tag input, used for roles and locations. */
function TokenList({ items, tone = "soft" }) {
    return (
        <div className="flex flex-wrap gap-2">
            {items.map((it) => (
                <span
                    key={it}
                    className={cn(
                        "inline-flex items-center gap-2 rounded-sm px-2.5 py-1.5 text-[13px]",
                        tone === "soft"
                            ? "bg-primary-tint text-accent-foreground"
                            : "bg-secondary text-muted-foreground"
                    )}
                >
                    {it}
                    <span className="cursor-pointer text-[15px] leading-none opacity-45 hover:opacity-100">
                        ×
                    </span>
                </span>
            ))}
            <span className="inline-flex cursor-pointer items-center gap-1.5 rounded-sm border border-dashed border-border px-2.5 py-1.5 text-[13px] text-muted-foreground hover:border-primary hover:text-primary">
                + add
            </span>
        </div>
    );
}

export { Field, Input, Textarea, TokenList };
