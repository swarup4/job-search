import Link from "next/link";
import {
    Building2, ChevronDown, Clock, LayoutGrid, List, MapPin, SlidersHorizontal,
} from "lucide-react";
import { AppShell } from "@/layout/AppShell";
import { PageHeader } from "@/layout/PageHeader";
import { MatchScore } from "@/component/MatchScore";
import { Signal } from "@/component/Signal";
import { Badge } from "@/component/ui/badge";
import { Panel } from "@/component/ui/panel";
import { Button, buttonVariants } from "@/component/ui/button";
import { ROUTES } from "@/routes";
import shortlist from "@/data/shortlist.json";
import board from "@/data/board.json";
import { cn } from "@/util/cn";

export default function Page() {
    return (
        <AppShell
            active={ROUTES.shortlist}
            counts={{
                pending: board.pending.keywordSelections + board.pending.applicationsToSubmit,
                newJobs: shortlist.discovered,
            }}
        >
            <PageHeader
                title="Today's shortlist"
                subtitle={`${shortlist.discovered} new jobs discovered since ${shortlist.since}, scored against your resume.`}
            >
                <div className="flex items-center gap-2.5">
                    <Button variant="outline" size="sm">
                        <SlidersHorizontal />
                        All sources
                    </Button>
                    <Button variant="outline" size="sm">
                        Match
                        <ChevronDown />
                    </Button>
                    <div className="flex items-center gap-1 rounded-pill bg-secondary p-1">
                        <span className="grid size-8 place-items-center rounded-pill bg-card text-primary shadow-soft">
                            <List className="size-[15px]" />
                        </span>
                        <span className="grid size-8 place-items-center rounded-pill text-muted-foreground">
                            <LayoutGrid className="size-[15px]" />
                        </span>
                    </div>
                </div>
            </PageHeader>

            <div className="flex flex-col gap-4">
                {shortlist.jobs.map((job) => (
                    <Panel key={job.id} hover className="p-5">
                        <div className="flex flex-wrap items-center gap-x-5 gap-y-4">
                            <span className="grid size-14 shrink-0 place-items-center rounded-md bg-secondary text-muted-foreground">
                                <Building2 className="size-6" />
                            </span>

                            <div className="min-w-[240px] grow">
                                <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                                    <h3 className="text-[17px] font-medium leading-tight">{job.role}</h3>
                                    <Badge variant="source">{job.source}</Badge>
                                </div>
                                <p className="mt-1.5 text-[13.5px] text-muted-foreground">{job.company}</p>
                                <div className="mt-2.5 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-[13px] text-muted-foreground">
                                    <span className="inline-flex items-center gap-1.5">
                                        <MapPin className="size-[13px]" />
                                        {job.location}
                                    </span>
                                    <span className="inline-flex items-center gap-1.5">
                                        <Clock className="size-[13px]" />
                                        {job.posted}
                                    </span>
                                </div>
                            </div>

                            <div className="flex shrink-0 items-center gap-6">
                                <Tally n={job.present} label="present" />
                                <Tally n={job.missing} label="missing" />
                                <MatchScore value={job.match} size="lg" />
                            </div>

                            <div className="flex shrink-0 flex-col items-end gap-2.5">
                                {job.risks > 0 ? (
                                    <Signal kind="risk">
                                        {job.risks} risk {job.risks === 1 ? "flag" : "flags"}
                                    </Signal>
                                ) : (
                                    <span className="text-[12px] text-muted-foreground">no risk flags</span>
                                )}
                                <div className="flex items-center gap-2">
                                    <Link
                                        href={ROUTES.job(job.id)}
                                        className={buttonVariants({ variant: "outline", size: "sm" })}
                                    >
                                        View JD
                                    </Link>
                                    <Link
                                        href={ROUTES.keywords(job.id)}
                                        className={cn(
                                            buttonVariants({
                                                variant: job.match >= 80 ? "default" : "soft",
                                                size: "sm",
                                            })
                                        )}
                                    >
                                        Review
                                    </Link>
                                </div>
                            </div>
                        </div>
                    </Panel>
                ))}
            </div>

            <div className="mt-6 text-center">
                <Button variant="outline">
                    Show {shortlist.hidden} lower-scoring matches
                </Button>
            </div>
        </AppShell>
    );
}

function Tally({ n, label }) {
    return (
        <div className="text-center">
            <div className="text-[19px] font-semibold leading-none">{n}</div>
            <div className="mt-1 text-[12px] text-muted-foreground">{label}</div>
        </div>
    );
}
