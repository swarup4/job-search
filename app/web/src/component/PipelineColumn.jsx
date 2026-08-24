import { JobCard } from "@/component/JobCard";

export function PipelineColumn({ column }) {
    return (
        <section className="flex min-w-0 flex-col gap-3">
            <header className="flex items-center gap-2 px-1">
                <h2 className="text-[14px] font-medium">{column.label}</h2>
                <span className="grid h-5 min-w-5 place-items-center rounded-pill bg-secondary px-1.5 text-[11px] font-semibold text-muted-foreground">
                    {column.count}
                </span>
            </header>
            <div className="flex flex-col gap-3">
                {column.cards.map((card) => (
                    <JobCard key={card.id} card={card} />
                ))}
                {column.more ? (
                    <button className="rounded-md border border-dashed border-border py-2.5 text-[12.5px] text-muted-foreground transition-colors hover:border-primary hover:text-primary">
                        + {column.more} more
                    </button>
                ) : null}
            </div>
        </section>
    );
}
