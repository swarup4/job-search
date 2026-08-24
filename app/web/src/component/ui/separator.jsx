import { cn } from "@/util/cn";

function Separator({ className, orientation = "horizontal", ...props }) {
    return (
        <div
            role="separator"
            className={cn(
                "shrink-0 bg-border",
                orientation === "horizontal" ? "h-px w-full" : "w-px self-stretch",
                className
            )}
            {...props}
        />
    );
}

export { Separator };
