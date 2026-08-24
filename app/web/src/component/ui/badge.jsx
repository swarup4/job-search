import { cva } from "class-variance-authority";
import { cn } from "@/util/cn";

const badgeVariants = cva(
    "inline-flex w-fit shrink-0 items-center justify-center gap-1 whitespace-nowrap rounded-sm px-2 py-[3px] text-[12px] leading-none [&>svg]:size-3",
    {
        variants: {
            variant: {
                default: "bg-primary text-primary-foreground font-medium",
                soft: "bg-primary-tint text-accent-foreground font-medium",
                outline: "border border-border bg-card text-muted-foreground",
                muted: "bg-secondary text-muted-foreground",
                source: "bg-secondary font-mono text-[11px] text-muted-foreground",
                risk: "bg-risk text-risk-ink font-medium",
                attention: "bg-attention text-attention-ink font-medium",
            },
        },
        defaultVariants: { variant: "default" },
    }
);

function Badge({ className, variant, ...props }) {
    return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
