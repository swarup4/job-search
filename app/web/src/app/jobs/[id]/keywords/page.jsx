"use client";

import { useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import Link from "next/link";
import { AlertTriangle, ArrowRight, Check, ChevronLeft, Quote } from "lucide-react";
import { Badge } from "@/component/ui/badge";
import { Button, buttonVariants } from "@/component/ui/button";
import { Checkbox } from "@/component/ui/checkbox";
import { Panel, PanelBody, PanelHeader, PanelTitle } from "@/component/ui/panel";
import { AppShell } from "@/layout/AppShell";
import { MatchScore } from "@/component/MatchScore";
import { ROUTES, sectionFor } from "@/routes";
import matches from "@/data/matches.json";
import board from "@/data/board.json";
import search from "@/data/search.json";
import { cn } from "@/util/cn";

export default function Page() {
  const { id: jobId } = useParams();
  const from = useSearchParams().get("from") ?? undefined;

    const detail = matches[jobId] ?? matches.acme;

    /** FR-2.5 — starts empty, and no code path seeds it. */
    const [selected, setSelected] = useState(() => new Set());

    const toggle = (id) =>
        setSelected((prev) => {
            const next = new Set(prev);
            next.has(id) ? next.delete(id) : next.add(id);
            return next;
        });

    const count = selected.size;

    return (
        <AppShell
            active={sectionFor(from)}
            counts={{
        pending: board.pending.keywordSelections + board.pending.applicationsToSubmit,
        shortlisted: search.shortlistedCount,
      }}
        >
            <div className="mb-5 flex flex-wrap items-center gap-4">
                <Link
                    href={ROUTES.job(jobId, from)}
                    className="inline-flex items-center gap-1.5 text-[13.5px] text-muted-foreground hover:text-primary"
                >
                    <ChevronLeft className="size-4" />
                    Back to job
                </Link>
                <span className="grow" />
                <MatchScore value={detail.match} size="sm" />
                <span className="text-[13px] text-muted-foreground">match</span>
            </div>

            <Panel className="p-6">
                <h1 className="text-[24px] font-semibold leading-tight tracking-tight">
                    Choose what goes into your resume
                </h1>
                <p className="mt-2 max-w-[74ch] text-[14px] leading-relaxed text-pretty text-muted-foreground">
                    <span className="font-medium text-foreground">{detail.role}</span> at{" "}
                    {detail.company.name}. Nothing below is added unless you check it — the keywords on
                    the left are already in your resume and shown for context only.
                </p>
            </Panel>

            <div className="mt-5 grid gap-5 xl:grid-cols-[minmax(0,0.85fr)_minmax(0,1fr)]">
                {/* PRESENT */}
                <Panel className="self-start">
                    <PanelHeader>
                        <PanelTitle>Already in your resume</PanelTitle>
                        <Badge variant="soft">{detail.present.length}</Badge>
                        <span className="grow" />
                        <span className="text-[12px] text-muted-foreground">read-only</span>
                    </PanelHeader>
                    <PanelBody>
                        <div className="flex flex-wrap gap-2">
                            {detail.present.map((kw) => (
                                <span
                                    key={kw}
                                    className="inline-flex items-center gap-1.5 rounded-sm bg-primary-tint px-2.5 py-1.5 text-[13px] text-accent-foreground"
                                >
                                    <Check className="size-[12px] stroke-[3]" />
                                    {kw}
                                </span>
                            ))}
                        </div>
                    </PanelBody>
                </Panel>

                <div className="flex flex-col gap-5">
                    {/* MISSING */}
                    <Panel>
                        <PanelHeader>
                            <PanelTitle>Missing from your resume</PanelTitle>
                            <Badge variant="outline">{detail.missing.length}</Badge>
                            <span className="grow" />
                            <span className="text-[12px] font-medium text-attention-muted">
                                none selected by default
                            </span>
                        </PanelHeader>
                        <ul>
                            {detail.missing.map((kw, i) => {
                                const checked = selected.has(kw.id);
                                return (
                                    <li key={kw.id}>
                                        <button
                                            type="button"
                                            onClick={() => toggle(kw.id)}
                                            className={cn(
                                                "flex w-full items-start gap-3.5 px-5 py-4 text-left transition-colors",
                                                i < detail.missing.length - 1 && "border-b border-border",
                                                checked ? "bg-primary-wash" : "hover:bg-secondary/60"
                                            )}
                                        >
                                            <Checkbox
                                                checked={checked}
                                                onCheckedChange={() => toggle(kw.id)}
                                                className="pointer-events-none mt-0.5"
                                            />
                                            <div className="min-w-0 grow">
                                                <div className="flex flex-wrap items-center gap-2.5">
                                                    <span
                                                        className={cn(
                                                            "text-[14.5px]",
                                                            checked ? "font-medium text-foreground" : "text-foreground"
                                                        )}
                                                    >
                                                        {kw.label}
                                                    </span>
                                                    <Badge variant="muted">
                                                        {kw.mentions} {kw.mentions === 1 ? "mention" : "mentions"}
                                                    </Badge>
                                                </div>
                                                <p className="mt-2 inline-flex items-start gap-2 rounded-sm bg-secondary px-2.5 py-1.5 font-mono text-[12px] leading-relaxed text-pretty text-muted-foreground">
                                                    <Quote className="mt-0.5 size-[11px] shrink-0" />
                                                    {kw.evidence}
                                                </p>
                                            </div>
                                        </button>
                                    </li>
                                );
                            })}
                        </ul>
                    </Panel>

                    {/* RISK — not selectable */}
                    <Panel className="overflow-hidden">
                        <div className="flex items-center gap-3 bg-risk px-5 py-3.5">
                            <AlertTriangle className="size-[15px] shrink-0 text-risk-ink" />
                            <h2 className="text-[14px] font-medium text-risk-ink">Risk flags</h2>
                            <Badge variant="risk">{detail.risks.length}</Badge>
                            <span className="grow" />
                            <span className="text-[12px] text-risk-muted">not selectable</span>
                        </div>
                        <div>
                            {detail.risks.map((risk, i) => (
                                <div
                                    key={risk.id}
                                    className={cn(
                                        "px-5 py-4",
                                        i < detail.risks.length - 1 && "border-b border-border"
                                    )}
                                >
                                    <p className="text-[13.5px] font-medium">{risk.title}</p>
                                    <p className="mt-1.5 text-[13px] leading-relaxed text-pretty text-muted-foreground">
                                        {risk.detail}
                                    </p>
                                </div>
                            ))}
                        </div>
                    </Panel>
                </div>
            </div>

            {/* commit bar */}
            <Panel className="sticky bottom-5 mt-5 p-4">
                <div className="flex flex-wrap items-center gap-x-5 gap-y-3">
                    <div
                        className={cn(
                            "grid size-11 shrink-0 place-items-center rounded-md text-[18px] font-bold",
                            count === 0
                                ? "bg-secondary text-muted-foreground"
                                : "bg-primary text-primary-foreground"
                        )}
                    >
                        {count}
                    </div>
                    <div className="min-w-0">
                        <p className="text-[14px] font-medium">
                            {count === 0
                                ? "Nothing selected yet"
                                : `keyword${count === 1 ? "" : "s"} selected`}
                        </p>
                        <p className="mt-0.5 text-[12.5px] text-muted-foreground">
                            Only what you check is written into the .tex — no wording is invented.
                        </p>
                    </div>
                    <span className="grow" />
                    <Link
                        href={from === "shortlist" ? ROUTES.shortlist : ROUTES.search}
                        className={buttonVariants({ variant: "outline", size: "sm" })}
                    >
                        Skip this job
                    </Link>
                    {count === 0 ? (
                        <Button disabled size="sm">
                            Tailor resume
                            <ArrowRight />
                        </Button>
                    ) : (
                        <Link href={ROUTES.preview(jobId, from)} className={buttonVariants({ size: "sm" })}>
                            Tailor with {count} selected
                            <ArrowRight />
                        </Link>
                    )}
                </div>
            </Panel>
        </AppShell>
    );
}
