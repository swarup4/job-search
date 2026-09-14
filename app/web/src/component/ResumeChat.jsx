"use client";

import { Plug, SendHorizonal, Sparkles } from "lucide-react";

import { Panel, PanelHeader, PanelTitle } from "@/component/ui/panel";
import { Button } from "@/component/ui/button";
import { Textarea } from "@/component/ui/field";
import { cn } from "@/util/helper";

/**
 * Rectifying the resume by talking to it.
 *
 * Deliberately inert: the model calls belong to the `ai` tier and are reached through
 * `server` (.claude/rules/ai-tier.md). The layout stays so the screen reads correctly
 * and so wiring it up later is adding the call, not rebuilding the panel.
 */

const OPENING = {
    role: "assistant",
    text: "Tell me what to fix and I will rewrite only what your profile already claims — I cannot add an employer, a date, a metric or a technology that is not in My details.",
};

const PROMPTS = [
    "Tighten the summary to two lines",
    "Lead every bullet with the outcome",
    "Cut the jargon from my current role",
    "Make it fit on one page",
];

export function ResumeChat() {
    // One seeded turn, so the thread reads as a conversation rather than a blank box.
    const messages = [OPENING];

    return (
        <Panel className="flex flex-col overflow-hidden">
            <PanelHeader>
                <Sparkles className="size-[15px] text-muted-foreground" />
                <PanelTitle>Rectify with the model</PanelTitle>
            </PanelHeader>

            <div className="flex min-h-[280px] flex-col gap-3 overflow-y-auto px-5 py-4">
                {messages.map((message, i) => (
                    <Bubble key={i} role={message.role}>
                        {message.text}
                    </Bubble>
                ))}
            </div>

            <div className="border-t border-border px-5 py-3.5">
                <p className="text-[12px] font-medium text-muted-foreground">Try</p>
                <div className="mt-2 flex flex-wrap gap-1.5">
                    {PROMPTS.map((prompt) => (
                        <button
                            key={prompt}
                            type="button"
                            disabled
                            className="rounded-pill border border-border px-2.5 py-1 text-[12px] text-muted-foreground disabled:cursor-not-allowed disabled:opacity-60"
                        >
                            {prompt}
                        </button>
                    ))}
                </div>
            </div>

            <div className="flex flex-col gap-2.5 border-t border-border px-5 py-4">
                <Textarea
                    disabled
                    rows={3}
                    placeholder="Ask for a change…"
                    className="min-h-[76px] text-[13px] disabled:cursor-not-allowed disabled:opacity-60"
                />
                <div className="flex items-center gap-3">
                    <p className="text-[12px] text-muted-foreground">
                        Changes land in the resume above for you to accept.
                    </p>
                    <span className="grow" />
                    <Button size="sm" disabled>
                        <SendHorizonal />
                        Send
                    </Button>
                </div>
            </div>

            <div className="flex items-center gap-2 border-t border-border bg-well px-5 py-2.5">
                <Plug className="size-[13px] shrink-0 text-attention-muted" />
                <p className="text-[12px] text-attention-muted">
                    Needs the tailoring service — not connected yet.
                </p>
            </div>
        </Panel>
    );
}

function Bubble({ role, children }) {
    const mine = role === "user";
    return (
        <div className={cn("flex", mine && "justify-end")}>
            <p
                className={cn(
                    "max-w-[90%] rounded-md px-3 py-2.5 text-[13px] leading-relaxed text-pretty",
                    mine
                        ? "bg-primary text-primary-foreground"
                        : "bg-secondary text-foreground"
                )}
            >
                {children}
            </p>
        </div>
    );
}
