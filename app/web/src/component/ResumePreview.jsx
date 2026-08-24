"use client";

import { useMemo, useState } from "react";
import { Download, Eye, FileCode2, GitCompareArrows } from "lucide-react";
import { Badge } from "@/component/ui/badge";
import { Panel, PanelHeader } from "@/component/ui/panel";
import { buttonVariants } from "@/component/ui/button";
import { ResumeDocument } from "@/component/ResumeDocument";
import { TexDiff } from "@/component/TexDiff";
import { deriveHunks } from "@/util/resumeDoc";
import { texToBlocks } from "@/util/texToBlocks";
import { cn } from "@/util/cn";

const TABS = [
    { key: "preview", label: "Preview", icon: Eye },
    { key: "diff", label: "Diff", icon: GitCompareArrows },
    { key: "source", label: "Source", icon: FileCode2 },
];

/** Three views of one document, all rendered client-side from the same lines. */
export function ResumePreview({ doc, activeLine, onSelect }) {
    const [tab, setTab] = useState("preview");

    const source = useMemo(() => doc.lines.map((line) => line.text).join("\n") + "\n", [doc.lines]);
    const blocks = useMemo(() => texToBlocks(doc.lines), [doc.lines]);
    const hunks = useMemo(() => deriveHunks(doc.lines), [doc.lines]);

    return (
        <Panel className="overflow-hidden">
            <PanelHeader className="gap-2">
                <div className="flex items-center gap-1 rounded-pill bg-secondary p-1">
                    {TABS.map(({ key, label, icon: Icon }) => (
                        <button
                            key={key}
                            type="button"
                            onClick={() => setTab(key)}
                            className={cn(
                                "inline-flex h-8 items-center gap-1.5 rounded-pill px-3 text-[13px] transition-colors",
                                tab === key
                                    ? "bg-card text-primary shadow-soft"
                                    : "text-muted-foreground hover:text-foreground"
                            )}
                        >
                            <Icon className="size-[14px]" />
                            {label}
                        </button>
                    ))}
                </div>

                <span className="grow" />

                {tab === "diff" ? (
                    <>
                        <Badge variant="muted" className="text-added-gutter">+{doc.added}</Badge>
                        <Badge variant="muted">−{doc.removed}</Badge>
                    </>
                ) : (
                    <span className="font-mono text-[12px] text-muted-foreground">{doc.file}</span>
                )}

                {/* A real anchor, not a synthesised click — this codebase never fakes one. */}
                <a
                    href={`data:application/x-tex;charset=utf-8,${encodeURIComponent(source)}`}
                    download={doc.file}
                    className={buttonVariants({ variant: "outline", size: "sm" })}
                >
                    <Download />
                    .tex
                </a>
            </PanelHeader>

            {tab === "preview" ? (
                <ResumeDocument blocks={blocks} />
            ) : (
                <div
                    className={cn(
                        "overflow-x-auto py-3",
                        tab === "source" && "max-h-[70vh] overflow-y-auto"
                    )}
                >
                    <TexDiff
                        hunks={tab === "diff" ? hunks : doc.lines}
                        activeLine={activeLine}
                        onSelect={onSelect}
                    />
                </div>
            )}

            <div className="border-t border-border bg-well px-5 py-3">
                <p className="text-[12.5px] leading-relaxed text-pretty text-muted-foreground">
                    {tab === "preview" ? (
                        <>
                            Rendered from the {doc.lines.length}-line{" "}
                            <span className="font-mono">.tex</span> in the browser — no server
                            involved. It is HTML, not typeset output, so spacing and line breaks
                            will differ from a compiled PDF.
                        </>
                    ) : (
                        <>
                            {tab === "diff"
                                ? `Changed lines with context. Switch to Source for the whole ${doc.lines.length}-line file.`
                                : `The complete tailored document, ${doc.lines.length} lines.`}{" "}
                            Click a line to pick it for rewriting.
                        </>
                    )}
                </p>
            </div>
        </Panel>
    );
}
