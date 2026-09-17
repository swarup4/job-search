"use client";

import { useMemo, useState } from "react";
import { AlertTriangle, Download, Expand, Eye, FileCode2, Loader2 } from "lucide-react";

import { Panel, PanelBody, PanelHeader } from "@/component/ui/panel";
import { Button, buttonVariants } from "@/component/ui/button";
import { Dialog } from "@/component/ui/dialog";
import { ResumeDocument } from "@/component/ResumeDocument";
import { texToResume } from "@/util/texResume";
import { cn } from "@/util/helper";

const TABS = [
    { key: "preview", label: "Preview", icon: Eye },
    { key: "source", label: "Source", icon: FileCode2 },
];

/**
 * One `.tex` shown two ways: as the page it becomes, and as the source that is stored.
 *
 * Both the Resume screen and the review screen show the same document, so the tabs,
 * the download and the parse live here rather than in each of them.
 */
export function ResumeView({
    tex,
    filename,
    onDownloadPdf,
    busy = false,
    busyLabel = "Rendering…",
    error = null,
}) {
    const [tab, setTab] = useState("preview");
    const [full, setFull] = useState(false);
    const [compiling, setCompiling] = useState(false);
    const blocks = useMemo(() => (tex ? texToResume(tex) : []), [tex]);

    async function savePdf() {
        setCompiling(true);
        try {
            await onDownloadPdf();
        } finally {
            setCompiling(false);
        }
    }

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

                {tex ? (
                    <>
                        <span className="hidden font-mono text-[12px] text-muted-foreground sm:inline">
                            {filename}
                        </span>
                        {/* Only on Preview: from the Source tab a full-size *page*
                            is not what the button appears to promise. */}
                        {tab === "preview" ? (
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={() => setFull(true)}
                                title="View full size"
                            >
                                <Expand />
                                Fullscreen
                            </Button>
                        ) : null}
                        {/* Each tab offers the thing it is showing: the page as a PDF,
                            the source as the .tex it is. */}
                        {tab === "preview" ? (
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={savePdf}
                                disabled={compiling}
                                title="Compile and download as PDF"
                            >
                                {compiling ? <Loader2 className="animate-spin" /> : <Download />}
                                .pdf
                            </Button>
                        ) : (
                            /* A real anchor, not a synthesised click — this codebase never fakes one. */
                            <a
                                href={`data:application/x-tex;charset=utf-8,${encodeURIComponent(tex)}`}
                                download={filename}
                                className={buttonVariants({ variant: "outline", size: "sm" })}
                            >
                                <Download />
                                .tex
                            </a>
                        )}
                    </>
                ) : null}
            </PanelHeader>

            {error ? (
                <PanelBody className="py-8">
                    <p className="flex items-start gap-2 text-[13px] text-risk-ink">
                        <AlertTriangle className="mt-0.5 size-[14px] shrink-0" />
                        {error}
                    </p>
                </PanelBody>
            ) : busy || !tex ? (
                <PanelBody className="flex items-center gap-2.5 py-16 text-[13px] text-muted-foreground">
                    <Loader2 className="size-[14px] animate-spin" />
                    {busyLabel}
                </PanelBody>
            ) : tab === "preview" ? (
                <ResumeDocument blocks={blocks} />
            ) : (
                <pre className="max-h-[70vh] overflow-auto bg-well px-5 py-4 font-mono text-[12px] leading-relaxed">
                    {tex}
                </pre>
            )}

            <div className="border-t border-border bg-well px-5 py-3">
                <p className="text-[12.5px] leading-relaxed text-pretty text-muted-foreground">
                    {tab === "preview"
                        ? "Rendered from the .tex in the browser — it is HTML, not typeset output, so spacing and line breaks will differ from a compiled PDF."
                        : "The exact source that is stored. Nothing is rewritten on the way to the database."}
                </p>
            </div>

            {/* The dialog is the width of the page itself, so the document runs edge
                to edge with no surround — `max-w` at 840 is PAGE_WIDTH, not a guess. */}
            <Dialog
                bare
                open={full}
                onClose={() => setFull(false)}
                title={filename ?? "Resume"}
                className="max-w-[840px]"
            >
                <ResumeDocument blocks={blocks} className="p-0" />
            </Dialog>
        </Panel>
    );
}
