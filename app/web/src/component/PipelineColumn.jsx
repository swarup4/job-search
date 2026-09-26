import { JobCard } from "@/component/JobCard";

/**
 * One board column. `count` is the column's real total from the API; the cards are
 * the first pages of it, and "Show more" asks for the next page.
 */
export function PipelineColumn({ label, empty, count, cards, loadingMore, error, onMore }) {
    const remaining = count - cards.length;

    return (
        <section className="flex min-w-0 flex-col gap-3">
            <header className="flex items-center gap-2 px-1">
                <h2 className="text-[14px] font-medium">{label}</h2>
                <span className="grid h-5 min-w-5 place-items-center rounded-pill bg-secondary px-1.5 text-[11px] font-semibold text-muted-foreground">
                    {count}
                </span>
            </header>
            <div className="flex flex-col gap-3">
                {cards.length ? (
                    cards.map((card) => <JobCard key={card.id} card={card} />)
                ) : (
                    <p className="rounded-md border border-dashed border-border px-3 py-4 text-center text-[12.5px] text-muted-foreground">
                        {empty}
                    </p>
                )}
                {error ? <p className="px-1 text-[12px] text-risk-ink">{error}</p> : null}
                {remaining > 0 ? (
                    <button
                        type="button"
                        onClick={onMore}
                        disabled={loadingMore}
                        className="rounded-md border border-dashed border-border py-2.5 text-[12.5px] text-muted-foreground transition-colors hover:border-primary hover:text-primary disabled:cursor-wait disabled:opacity-60"
                    >
                        {loadingMore ? "Loading…" : `Show more (${remaining} left)`}
                    </button>
                ) : null}
            </div>
        </section>
    );
}
