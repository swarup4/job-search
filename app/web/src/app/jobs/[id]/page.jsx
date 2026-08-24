import Link from "next/link";
import {
    ArrowRight, Briefcase, Building2, CalendarClock, Clock, ExternalLink,
    Globe, MapPin, Users, Wallet,
} from "lucide-react";
import { AppShell } from "@/layout/AppShell";
import { MatchScore } from "@/component/MatchScore";
import { Signal } from "@/component/Signal";
import { Badge } from "@/component/ui/badge";
import { Panel, PanelBody, PanelHeader, PanelTitle } from "@/component/ui/panel";
import { Button, buttonVariants } from "@/component/ui/button";
import { ShortlistButton } from "@/component/ShortlistButton";
import { ROUTES, sectionFor } from "@/routes";
import matches from "@/data/matches.json";
import board from "@/data/board.json";
import search from "@/data/search.json";
import { cn } from "@/util/cn";

export default async function Page({ params, searchParams }) {
  const { id: jobId } = await params;
  const { from } = await searchParams;

    const job = matches[jobId] ?? matches.acme;

    return (
        <AppShell
            active={sectionFor(from)}
            counts={{
        pending: board.pending.keywordSelections + board.pending.applicationsToSubmit,
        shortlisted: search.shortlistedCount,
      }}
        >
            {/* header panel */}
            <Panel className="p-6">
                <div className="flex flex-wrap items-start gap-x-6 gap-y-5">
                    <span className="grid size-16 shrink-0 place-items-center rounded-md bg-secondary text-muted-foreground">
                        <Building2 className="size-7" />
                    </span>

                    <div className="min-w-[260px] grow">
                        <div className="flex flex-wrap items-center gap-3">
                            <h1 className="text-[26px] font-semibold leading-tight tracking-tight">
                                {job.role}
                            </h1>
                            <Badge variant="soft">{job.type}</Badge>
                        </div>
                        <p className="mt-2 text-[15px] text-muted-foreground">{job.company.name}</p>
                        <div className="mt-3.5 flex flex-wrap items-center gap-x-5 gap-y-2 text-[13.5px] text-muted-foreground">
                            <Meta icon={MapPin}>{job.location}</Meta>
                            <Meta icon={Clock}>Posted {job.posted}</Meta>
                            <Meta icon={Wallet}>{job.salary}</Meta>
                            <Meta icon={Briefcase}>{job.experience}</Meta>
                            <Badge variant="source">{job.source}</Badge>
                        </div>
                    </div>

                    <div className="flex shrink-0 flex-col items-center gap-3">
                        <MatchScore value={job.match} size="lg" />
                        <span className="text-[12px] text-muted-foreground">match</span>
                    </div>
                </div>

                <div className="mt-6 flex flex-wrap items-center gap-3 border-t border-border pt-5">
                    <Link href={ROUTES.keywords(jobId, from)} className={buttonVariants()}>
                        Review keywords
                        <ArrowRight />
                    </Link>
                    <Button variant="outline">
                        <ExternalLink />
                        Open original posting
                    </Button>
                    <ShortlistButton shortlisted={job.shortlisted} />
                    <span className="grow" />
                    <span className="inline-flex items-center gap-1.5 text-[13px] text-muted-foreground">
                        <CalendarClock className="size-[14px]" />
                        Closes {job.deadline}
                    </span>
                </div>
            </Panel>

            <div className="mt-5 grid gap-5 xl:grid-cols-[minmax(0,1fr)_340px]">
                {/* JD body */}
                <div className="flex flex-col gap-5">
                    <Panel>
                        <PanelHeader><PanelTitle>Role summary</PanelTitle></PanelHeader>
                        <PanelBody>
                            <p className="text-[14.5px] leading-relaxed text-pretty text-muted-foreground">
                                {job.summary}
                            </p>
                        </PanelBody>
                    </Panel>

                    <Panel>
                        <PanelHeader><PanelTitle>Responsibilities</PanelTitle></PanelHeader>
                        <PanelBody>
                            <ul className="flex flex-col gap-3">
                                {job.responsibilities.map((r) => (
                                    <li key={r} className="flex gap-3 text-[14px] leading-relaxed">
                                        <span className="mt-[7px] size-1.5 shrink-0 rounded-full bg-primary" />
                                        <span className="text-muted-foreground">{r}</span>
                                    </li>
                                ))}
                            </ul>
                        </PanelBody>
                    </Panel>

                    <Panel>
                        <PanelHeader><PanelTitle>Requirements</PanelTitle></PanelHeader>
                        <PanelBody>
                            <ul className="flex flex-col gap-3">
                                {job.requirements.map((r) => (
                                    <li key={r} className="flex gap-3 text-[14px] leading-relaxed">
                                        <span className="mt-[7px] size-1.5 shrink-0 rounded-full bg-primary" />
                                        <span className="text-muted-foreground">{r}</span>
                                    </li>
                                ))}
                            </ul>
                        </PanelBody>
                    </Panel>

                    {/* the agent's read on this JD — what makes this page JobPilot's, not a job board's */}
                    <Panel>
                        <PanelHeader>
                            <PanelTitle>What the match agent found</PanelTitle>
                            <span className="grow" />
                            <Link
                                href={ROUTES.keywords(jobId, from)}
                                className="text-[13px] font-medium text-primary hover:underline"
                            >
                                Review &amp; select
                            </Link>
                        </PanelHeader>
                        <PanelBody className="flex flex-col gap-5">
                            <div>
                                <p className="mb-2.5 text-[13px] font-medium">
                                    In your resume
                                    <span className="ml-2 text-muted-foreground">{job.present.length}</span>
                                </p>
                                <div className="flex flex-wrap gap-1.5">
                                    {job.present.slice(0, 12).map((k) => (
                                        <Badge key={k} variant="soft">{k}</Badge>
                                    ))}
                                    {job.present.length > 12 ? (
                                        <Badge variant="muted">+{job.present.length - 12}</Badge>
                                    ) : null}
                                </div>
                            </div>
                            <div>
                                <p className="mb-2.5 text-[13px] font-medium">
                                    Missing
                                    <span className="ml-2 text-muted-foreground">{job.missing.length}</span>
                                    <span className="ml-2 text-[12px] font-normal text-attention-muted">
                                        nothing is added unless you check it
                                    </span>
                                </p>
                                <div className="flex flex-wrap gap-1.5">
                                    {job.missing.map((k) => (
                                        <Badge key={k.id} variant="outline">{k.label}</Badge>
                                    ))}
                                </div>
                            </div>
                            <div className="flex flex-col gap-2.5">
                                {job.risks.map((r) => (
                                    <Signal key={r.id} kind="risk" className="items-start">
                                        {r.title}
                                    </Signal>
                                ))}
                            </div>
                        </PanelBody>
                    </Panel>
                </div>

                {/* company rail — adapted from the reference's employer-details page */}
                <div className="flex flex-col gap-5">
                    <Panel>
                        <PanelHeader><PanelTitle>Company</PanelTitle></PanelHeader>
                        <PanelBody className="flex flex-col gap-4">
                            <div className="flex items-center gap-3">
                                <span className="grid size-12 shrink-0 place-items-center rounded-md bg-secondary text-muted-foreground">
                                    <Building2 className="size-5" />
                                </span>
                                <div className="min-w-0">
                                    <p className="truncate text-[15px] font-medium">{job.company.name}</p>
                                    <p className="truncate text-[12.5px] text-muted-foreground">
                                        {job.company.industry}
                                    </p>
                                </div>
                            </div>
                            <p className="text-[13.5px] leading-relaxed text-pretty text-muted-foreground">
                                {job.company.blurb}
                            </p>
                            <dl className="flex flex-col divide-y divide-border">
                                <Row icon={Users} label="Size">{job.company.size}</Row>
                                <Row icon={CalendarClock} label="Founded">{job.company.founded}</Row>
                                <Row icon={Globe} label="Website">{job.company.site}</Row>
                                <Row icon={MapPin} label="Workplace">{job.workplace}</Row>
                                <Row icon={Users} label="Applicants">{job.applicants}</Row>
                            </dl>
                        </PanelBody>
                    </Panel>

                    <Panel>
                        <PanelHeader><PanelTitle>Next step</PanelTitle></PanelHeader>
                        <PanelBody className="flex flex-col gap-3">
                            <p className="text-[13.5px] leading-relaxed text-muted-foreground">
                                Selecting keywords is the only way a resume gets tailored for this job. Nothing
                                is written without your explicit choice.
                            </p>
                            <Link
                                href={ROUTES.keywords(jobId, from)}
                                className={cn(buttonVariants(), "w-full")}
                            >
                                Review {job.missing.length} missing keywords
                            </Link>
                        </PanelBody>
                    </Panel>
                </div>
            </div>
        </AppShell>
    );
}

function Meta({ icon: Icon, children }) {
    return (
        <span className="inline-flex items-center gap-1.5">
            <Icon className="size-[14px]" />
            {children}
        </span>
    );
}

function Row({ icon: Icon, label, children }) {
    return (
        <div className="flex items-center gap-3 py-2.5">
            <Icon className="size-[14px] shrink-0 text-muted-foreground" />
            <dt className="text-[13px] text-muted-foreground">{label}</dt>
            <span className="grow" />
            <dd className="text-[13px] font-medium">{children}</dd>
        </div>
    );
}
