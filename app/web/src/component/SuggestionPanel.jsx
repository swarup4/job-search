"use client";

import { MapPin, Plug, Sparkles, Wand2, X } from "lucide-react";
import { Badge } from "@/component/ui/badge";
import { Button } from "@/component/ui/button";
import { Panel, PanelBody, PanelHeader, PanelTitle } from "@/component/ui/panel";
import { Textarea } from "@/component/ui/field";

/**
 * The tailoring suggestions UI with its model calls removed.
 *
 * Both actions are deliberately inert: they need a tailoring service that does not
 * exist yet. Generation belongs to the `ai` tier and is reached through `server`
 * (.claude/rules/ai-tier.md) — app/web is a pure client and makes no network calls.
 * The layout stays so the screen reads correctly and so wiring it up later is a matter
 * of adding the call, not rebuilding the panel.
 */
export function SuggestionPanel({ keywords, activeLine, onDismiss }) {
    return (
        <div className="flex flex-col gap-5">
            <Panel>
                <PanelHeader>
                    <MapPin className="size-[15px] text-muted-foreground" />
                    <PanelTitle>Where these belong</PanelTitle>
                    <Badge variant="soft">{keywords.length}</Badge>
                    <span className="grow" />
                    <Button variant="soft" size="sm" disabled>
                        <Sparkles />
                        Ask the model
                    </Button>
                </PanelHeader>
                <PanelBody>
                    <p className="text-[13px] leading-relaxed text-pretty text-muted-foreground">
                        For each keyword you approved, this will point at the section it honestly
                        fits — or say it fits nowhere. It never writes resume prose.
                    </p>
                </PanelBody>
                <NotWired />
            </Panel>

            {activeLine ? (
                <Panel>
                    <PanelHeader>
                        <Wand2 className="size-[15px] text-muted-foreground" />
                        <PanelTitle>Rewrite line {activeLine.n}</PanelTitle>
                        <span className="grow" />
                        <button
                            type="button"
                            onClick={onDismiss}
                            aria-label="Close"
                            className="text-muted-foreground hover:text-foreground"
                        >
                            <X className="size-4" />
                        </button>
                    </PanelHeader>

                    <PanelBody className="flex flex-col gap-4">
                        <div>
                            <p className="text-[12px] font-medium text-muted-foreground">current</p>
                            <p className="mt-1.5 whitespace-pre-wrap rounded-sm bg-secondary px-3 py-2 font-mono text-[12px] leading-relaxed">
                                {activeLine.text}
                            </p>
                        </div>

                        <label className="flex flex-col gap-2">
                            <span className="text-[13px] font-medium text-muted-foreground">
                                What should change?
                            </span>
                            <Textarea
                                disabled
                                placeholder="e.g. lead with the outcome, drop the jargon, make it one clause shorter"
                                className="min-h-[76px] text-[13px] disabled:cursor-not-allowed disabled:opacity-60"
                            />
                        </label>

                        <Button size="sm" disabled className="self-start">
                            <Sparkles />
                            Suggest a rewrite
                        </Button>
                    </PanelBody>
                    <NotWired />
                </Panel>
            ) : (
                <Panel>
                    <PanelHeader>
                        <Wand2 className="size-[15px] text-muted-foreground" />
                        <PanelTitle>Rewrite a line</PanelTitle>
                    </PanelHeader>
                    <PanelBody>
                        <p className="text-[13px] leading-relaxed text-pretty text-muted-foreground">
                            Click any line in the diff or source to pick it for rewriting. A rewrite
                            may only reword what the line already claims — it cannot add an
                            employer, a date, a metric or a technology you have not approved.
                        </p>
                    </PanelBody>
                    <NotWired />
                </Panel>
            )}
        </div>
    );
}

function NotWired() {
    return (
        <div className="flex items-center gap-2 border-t border-border bg-well px-5 py-2.5">
            <Plug className="size-[13px] shrink-0 text-attention-muted" />
            <p className="text-[12px] text-attention-muted">
                Needs the tailoring service — not connected yet.
            </p>
        </div>
    );
}
