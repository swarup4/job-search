import { cn } from "@/util/cn";

export function SettingRow({ label, hint, children, last = false }) {
    return (
        <div
            className={cn(
                "flex flex-wrap items-center gap-x-5 gap-y-2 px-5 py-4",
                !last && "border-b border-border"
            )}
        >
            <div className="min-w-[200px] grow">
                <p className="text-[14px] font-medium">{label}</p>
                {hint ? (
                    <p className="mt-1 max-w-[62ch] text-[12.5px] leading-relaxed text-muted-foreground">
                        {hint}
                    </p>
                ) : null}
            </div>
            <div className="shrink-0">{children}</div>
        </div>
    );
}
