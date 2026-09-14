"use client";

import { useLayoutEffect, useRef, useState } from "react";

import { cn } from "@/util/helper";

/** The page's true width. Everything inside is laid out against this, never against
 *  the column it happens to be sitting in. */
const PAGE_WIDTH = 840;

/**
 * The resume as a page, not as source.
 *
 * This is the one component that deliberately does NOT use the app's design tokens.
 * It depicts a printed page, which is white in both themes — `bg-card` would turn the
 * paper dark and `text-primary` would wash the accent out, so ink and paper are fixed
 * utilities here. Everything outside the page still uses tokens.
 *
 * The page is a FIXED width and deliberately not responsive: a resume is printed at
 * one size, and reflowing it into a narrow column would show a layout that does not
 * exist in the document being approved. A narrow column shrinks the whole page
 * instead — see `FitToWidth` — so the proportions are always the real ones.
 */
export function ResumeDocument({ blocks, className }) {
    return (
        <div className={cn("bg-well px-6 py-8", className)}>
            <FitToWidth>
                <article className="w-[840px] bg-white px-14 py-12 text-slate-800 shadow-card">
                    {group(blocks).map((block, i) => (
                        <Block key={i} block={block} first={i === 0} />
                    ))}
                </article>
            </FitToWidth>
        </div>
    );
}

/**
 * Scales a fixed-width page down until it fits the space available, and never up —
 * past full size there is nothing to gain, so a wide column just centres the page.
 *
 * A transform does not change layout size, so the scaled page would still reserve its
 * full 840px of width and height. The measured height is put back on the wrapper to
 * close that gap.
 */
function FitToWidth({ children }) {
    const holder = useRef(null);
    const page = useRef(null);
    const [fit, setFit] = useState({ scale: 1, height: undefined });

    // Layout effect, not effect: measuring after paint would show one frame of the
    // page at full width before it shrinks.
    useLayoutEffect(() => {
        const holderEl = holder.current;
        const pageEl = page.current;
        if (!holderEl || !pageEl) return undefined;

        const measure = () => {
            const available = holderEl.clientWidth;
            if (!available) return;

            const scale = Math.min(1, available / PAGE_WIDTH);
            const height = pageEl.offsetHeight * scale;

            // Same numbers, same object — otherwise writing the height back onto the
            // wrapper re-triggers the observer that just measured it.
            setFit((was) =>
                Math.abs(was.scale - scale) < 0.001 && Math.abs((was.height ?? 0) - height) < 0.5
                    ? was
                    : { scale, height }
            );
        };

        measure();

        // The page is observed too: its height changes with the content, and the
        // wrapper has to follow it.
        const observer = new ResizeObserver(measure);
        observer.observe(holderEl);
        observer.observe(pageEl);
        return () => observer.disconnect();
    }, []);

    return (
        <div ref={holder} className="overflow-hidden" style={{ height: fit.height }}>
            <div
                ref={page}
                className="mx-auto w-[840px] origin-top-left"
                style={{ transform: `scale(${fit.scale})` }}
            >
                {children}
            </div>
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

function Bullets({ items }) {
    if (!items.length) return null;
    return (
        <ul className="mt-1.5 list-disc space-y-1 pl-5">
            {items.map((item, i) => (
                <li key={i} className="text-[12.5px] leading-snug text-pretty text-slate-700">
                    {item}
                </li>
            ))}
        </ul>
    );
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
                    {block.rows.map((row, i) => (
                        <div key={i} className="col-span-2 grid grid-cols-subgrid">
                            {/* A grid template loses the group names — the row is the grouping. */}
                            {row.label ? (
                                <dt className="text-[12.5px] font-semibold text-slate-900">{row.label}</dt>
                            ) : null}
                            <dd
                                className={cn(
                                    "text-[12.5px] leading-snug text-slate-700",
                                    row.label || "col-span-2"
                                )}
                            >
                                {row.value}
                            </dd>
                        </div>
                    ))}
                </dl>
            );

        case "pills":
            return (
                <div className="mt-3 flex flex-wrap gap-1.5">
                    {block.items.map((item) => (
                        <span
                            key={item}
                            className="rounded-pill bg-slate-100 px-2.5 py-1 text-[11.5px] text-slate-700"
                        >
                            {item}
                        </span>
                    ))}
                </div>
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
                    <Bullets items={block.bullets} />
                    {(block.projects ?? []).map((project) => (
                        <div key={project.name} className="mt-2">
                            <p className="text-[12.5px] font-semibold italic text-slate-800">
                                {project.name}
                            </p>
                            <Bullets items={project.bullets} />
                        </div>
                    ))}
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
                        {[block.institution, block.location].filter(Boolean).join(" — ")}
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
