import { AlertTriangle, Clock } from "lucide-react";
import { cn } from "@/util/cn";

/** kind: "attention" (you must act) | "risk" (a concern was surfaced) */
export function Signal({ kind, children, className }) {
    const Icon = kind === "risk" ? AlertTriangle : Clock;
    return (
        <span
            className={cn(
                "inline-flex items-center gap-1.5 rounded-sm px-2 py-1 text-[12px] font-medium",
                kind === "risk" ? "bg-risk text-risk-ink" : "bg-attention text-attention-ink",
                className
            )}
        >
            <Icon className="size-[12px] shrink-0" />
            {children}
        </span>
    );
}
