import { cn } from "@/util/cn";

/** White, 4px, ambient shadow, no border — the reference template's card. */
function Panel({ className, hover = false, ...props }) {
    return (
        <div
            className={cn(
                "panel",
                hover && "transition-shadow hover:shadow-raise",
                className
            )}
            {...props}
        />
    );
}

function PanelHeader({ className, ...props }) {
    return (
        <div
            className={cn("flex items-center gap-3 border-b border-border px-5 py-4", className)}
            {...props}
        />
    );
}

function PanelTitle({ className, ...props }) {
    return <h2 className={cn("widget-title", className)} {...props} />;
}

function PanelBody({ className, ...props }) {
    return <div className={cn("px-5 py-4", className)} {...props} />;
}

export { Panel, PanelHeader, PanelTitle, PanelBody };
