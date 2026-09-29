"use client";

import { cn } from "@/util/helper";

const GUTTER = "w-12 shrink-0 select-none pr-3 text-right text-[11px]";
const MARKER = "w-4 shrink-0 select-none text-center";
const ROW = "flex items-start font-mono text-[12.5px] leading-[24px]";

/**
 * Renders .tex lines. A tailored line shows the version it replaced above it — a change you cannot see is a change
 * you cannot review.
 *
 * Removals are muted and struck through rather than red: this design system spends red
 * on risk flags only (see the palette note in globals.scss), so a red removal would
 * read as a warning.
 */
export function TexDiff({ hunks }) {
    return (
        <>
            {hunks.map((line, i) =>
                line.gap ? (
                    <div key={`gap-${i}`} className="my-2 ml-12 h-px bg-border" />
                ) : (
                    <Row key={line.n} line={line} />
                )
            )}
        </>
    );
}

function Row({ line }) {
    return (
        <div>
            {line.was ? (
                <div className={cn(ROW, "opacity-70")}>
                    <span className={cn(GUTTER, "text-muted-foreground/40")}>{line.n}</span>
                    <span className={cn(MARKER, "text-muted-foreground")}>−</span>
                    <span className="whitespace-pre pr-5 text-muted-foreground line-through">
                        {line.was}
                    </span>
                </div>
            ) : null}

            <div className={cn(ROW, line.add && "bg-added")}>
                <span
                    className={cn(
                        GUTTER,
                        line.add ? "text-added-gutter" : "text-muted-foreground/55"
                    )}
                >
                    {line.n}
                </span>
                <span className={cn(MARKER, line.add && "font-semibold text-added-gutter")}>
                    {line.add ? "+" : ""}
                </span>
                <span
                    className={cn(
                        "whitespace-pre pr-5",
                        line.add ? "text-added-ink" : "text-muted-foreground"
                    )}
                >
                    {line.text}
                </span>
            </div>
        </div>
    );
}
