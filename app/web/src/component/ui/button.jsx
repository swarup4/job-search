import { cva } from "class-variance-authority";
import { cn } from "@/util/cn";

const buttonVariants = cva(
    "inline-flex shrink-0 items-center justify-center gap-2 whitespace-nowrap rounded-pill text-[14px] font-medium transition-all outline-none disabled:pointer-events-none disabled:opacity-45 focus-visible:ring-[3px] focus-visible:ring-ring/35 [&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-4",
    {
        variants: {
            variant: {
                default: "bg-primary text-primary-foreground hover:bg-primary-hover",
                outline: "border border-border bg-card text-foreground hover:border-primary hover:text-primary",
                soft: "bg-primary-tint text-accent-foreground hover:bg-primary hover:text-primary-foreground",
                ghost: "text-muted-foreground hover:bg-secondary hover:text-foreground",
                attention: "bg-attention-solid text-white hover:brightness-95",
                attentionQuiet: "border border-attention-rule bg-card text-attention-ink hover:bg-attention",
                link: "text-primary underline-offset-4 hover:underline",
            },
            size: {
                default: "h-10 px-5",
                sm: "h-9 gap-1.5 px-4 text-[13px]",
                lg: "h-12 px-7 text-[15px]",
                icon: "size-10 rounded-md",
            },
        },
        defaultVariants: { variant: "default", size: "default" },
    }
);

function Button({ className, variant, size, ...props }) {
    return <button className={cn(buttonVariants({ variant, size }), className)} {...props} />;
}

export { Button, buttonVariants };
