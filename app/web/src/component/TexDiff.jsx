"use client";

import { Wand2 } from "lucide-react";
import { cn } from "@/util/cn";

const GUTTER = "w-12 shrink-0 select-none pr-3 text-right text-[11px]";
const MARKER = "w-4 shrink-0 select-none text-center";
const ROW = "flex items-start font-mono text-[12.5px] leading-[24px]";

/**
 * Renders .tex lines, each selectable so it can be picked for rewriting. A tailored
 * line shows the version it replaced above it — a change you cannot see is a change
 * you cannot review.
 *
 * Removals are muted and struck through rather than red: this design system spends red
 * on risk flags only (see the palette note in globals.scss), so a red removal would
 * read as a warning.
 */
export function TexDiff({ hunks, activeLine, onSelect }) {
    return (
        <>
            {hunks.map((line, i) =>
                line.gap ? (
                    <div key={`gap-${i}`} className="my-2 ml-12 h-px bg-border" />
                ) : (
                    <Row
                        key={line.n}
                        line={line}
                        active={activeLine === line.n}
                        onSelect={onSelect}
                    />
                )
            )}
        </>
    );
}

function Row({ line, active, onSelect }) {
    return (
        <div className={cn("transition-colors", active && "bg-primary-wash")}>
            {line.was ? (
                <div className={cn(ROW, "opacity-70")}>
                    <span className={cn(GUTTER, "text-muted-foreground/40")}>{line.n}</span>
                    <span className={cn(MARKER, "text-muted-foreground")}>−</span>
                    <span className="whitespace-pre pr-5 text-muted-foreground line-through">
                        {line.was}
                    </span>
                </div>
            ) : null}

            <button
                type="button"
                onClick={() => onSelect(line.n)}
                className={cn(
                    ROW,
                    "group w-full text-left",
                    line.add && "bg-added",
                    !active && "hover:bg-secondary/60"
                )}
            >
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
                <span className="grow" />
                <Wand2
                    className={cn(
                        "mr-4 mt-1.5 size-[13px] shrink-0 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100",
                        active && "text-primary opacity-100"
                    )}
                />
            </button>
        </div>
    );
}
