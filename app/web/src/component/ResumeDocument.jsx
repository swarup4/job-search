import { cn } from "@/util/cn";

/**
 * The resume as a page, not as source.
 *
 * This is the one component that deliberately does NOT use the app's design tokens.
 * It depicts a printed page, which is white in both themes — `bg-card` would turn the
 * paper dark and `text-primary` would wash the accent out, so ink and paper are fixed
 * utilities here. Everything outside the page still uses tokens.
 */
export function ResumeDocument({ blocks }) {
    return (
        <div className="overflow-x-auto bg-well px-6 py-8">
            <article className="mx-auto w-full max-w-[840px] bg-white px-14 py-12 text-slate-800 shadow-card">
                {group(blocks).map((block, i) => (
                    <Block key={i} block={block} first={i === 0} />
                ))}
            </article>
        </div>
    );
}

/** Consecutive skill and cert rows render as one table, so group them first. */
function group(blocks) {
    const out = [];
    for (const block of blocks) {
        const last = out[out.length - 1];
        if ((block.kind === "skill" || block.kind === "cert") && last?.kind === `${block.kind}s`) {
            last.rows.push(block);
        } else if (block.kind === "skill" || block.kind === "cert") {
            out.push({ kind: `${block.kind}s`, rows: [block] });
        } else {
            out.push(block);
        }
    }
    return out;
}

function Block({ block, first }) {
    switch (block.kind) {
        case "name":
            return (
                <h1 className="text-center text-[27px] font-bold leading-tight tracking-tight text-slate-900">
                    {block.text}
                </h1>
            );

        case "headerLine":
            return (
                <p className="mt-1.5 text-center text-[12.5px] leading-snug text-slate-500">
                    {block.text}
                </p>
            );

        case "section":
            return (
                <h2
                    className={cn(
                        "border-b border-slate-300 pb-1 text-[14.5px] font-semibold text-teal-700",
                        first ? "mt-0" : "mt-7"
                    )}
                >
                    {block.text}
                </h2>
            );

        case "paragraph":
            return (
                <p className="mt-2.5 text-[12.5px] leading-relaxed text-pretty text-slate-700">
                    {block.text}
                </p>
            );

        case "skills":
            return (
                <dl className="mt-3 grid grid-cols-[minmax(96px,auto)_1fr] gap-x-5 gap-y-1.5">
                    {block.rows.map((row) => (
                        <div key={row.label} className="col-span-2 grid grid-cols-subgrid">
                            <dt className="text-[12.5px] font-semibold text-slate-900">{row.label}</dt>
                            <dd className="text-[12.5px] leading-snug text-slate-700">{row.value}</dd>
                        </div>
                    ))}
                </dl>
            );

        case "job":
            return (
                <section className="mt-4">
                    <div className="flex items-baseline gap-3">
                        <h3 className="text-[13.5px] font-semibold text-slate-900">{block.title}</h3>
                        <span className="grow border-b border-dotted border-slate-300" />
                        <span className="shrink-0 text-[12px] italic text-slate-500">{block.dates}</span>
                    </div>
                    <p className="mt-0.5 text-[11.5px] font-medium uppercase tracking-wide text-slate-600">
                        {block.company}
                    </p>
                    <ul className="mt-1.5 list-disc space-y-1 pl-5">
                        {block.bullets.map((bullet, i) => (
                            <li key={i} className="text-[12.5px] leading-snug text-pretty text-slate-700">
                                {bullet}
                            </li>
                        ))}
                    </ul>
                </section>
            );

        case "degree":
            return (
                <section className="mt-3">
                    <div className="flex items-baseline gap-3">
                        <h3 className="text-[13.5px] font-semibold text-slate-900">{block.degree}</h3>
                        <span className="grow border-b border-dotted border-slate-300" />
                        <span className="shrink-0 text-[12px] italic text-slate-500">{block.dates}</span>
                    </div>
                    <p className="mt-0.5 text-[11.5px] font-medium uppercase tracking-wide text-slate-600">
                        {block.institution} — {block.location}
                    </p>
                </section>
            );

        case "certs":
            return (
                <ul className="mt-3 space-y-1.5">
                    {block.rows.map((row) => (
                        <li key={row.name} className="flex items-baseline gap-3">
                            <span className="text-[12.5px] text-slate-800">
                                {row.name}
                                <span className="text-slate-500"> · {row.issuer}</span>
                            </span>
                            <span className="grow border-b border-dotted border-slate-300" />
                            <span className="shrink-0 text-[12px] italic text-slate-500">{row.year}</span>
                        </li>
                    ))}
                </ul>
            );

        default:
            return null;
    }
}
