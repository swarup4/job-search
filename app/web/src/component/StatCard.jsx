import { cn } from "@/util/cn";

/** The reference's dashboard counter: white panel, tinted icon square, big number. */
export function StatCard({ icon: Icon, value, label, tone = "primary", note }) {
    const tones = {
        primary: "bg-primary-tint text-primary",
        attention: "bg-attention text-attention-ink",
        risk: "bg-risk text-risk-ink",
        muted: "bg-secondary text-muted-foreground",
    };
    return (
        <div className="panel flex items-center gap-4 px-5 py-[18px]">
            <span className={cn("grid size-12 shrink-0 place-items-center rounded-md", tones[tone])}>
                <Icon className="size-[21px]" />
            </span>
            <div className="min-w-0">
                <div className="text-[26px] font-bold leading-none">{value}</div>
                <div className="mt-1.5 truncate text-[13px] text-muted-foreground">{label}</div>
            </div>
            {note ? (
                <>
                    <span className="grow" />
                    <span className="shrink-0 text-[12px] text-muted-foreground">{note}</span>
                </>
            ) : null}
        </div>
    );
}
