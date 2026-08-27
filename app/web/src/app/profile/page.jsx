import {
    Award, Briefcase, Building2, FileText, GraduationCap, Layers, Link2, Mail,
    MapPin, Phone, Plus, RefreshCw, Save, Pencil,
} from "lucide-react";
import { AppShell } from "@/layout/AppShell";
import { PageHeader } from "@/layout/PageHeader";
import { Panel, PanelBody, PanelHeader, PanelTitle } from "@/component/ui/panel";
import { Field, Input, Textarea } from "@/component/ui/field";
import { Button } from "@/component/ui/button";
import { Badge } from "@/component/ui/badge";
import { ROUTES } from "@/routes";
import { getProfile, getShellCounts } from "@/services";
import { ProfileIdentity } from "@/component/ProfileIdentity";
import { EmptyProfile } from "@/component/EmptyProfile";
import { cn } from "@/util/cn";

// Reads live data through axios, which Next cannot see the way it sees its own
// fetch(). Without this the page is prerendered at build time and the profile is
// frozen into the bundle — and a build with the API down would fail outright.
export const dynamic = "force-dynamic";

export default async function Page() {
    const [profile, counts] = await Promise.all([getProfile(), getShellCounts()]);

    if (!profile) {
        return (
            <AppShell active={ROUTES.profile} counts={counts}>
                <EmptyProfile />
            </AppShell>
        );
    }

    const {
        personal = {},
        summary,
        experience = [],
        education = [],
        skill_groups: skillGroups = [],
        certifications = [],
    } = profile;
    const totalSkills = skillGroups.reduce((n, g) => n + g.items.length, 0);

    return (
        <AppShell active={ROUTES.profile} counts={counts}>
            <PageHeader
                title="My details"
                subtitle="Your resume material. Tailoring may only draw on what exists here — that constraint is what makes the no-fabrication rule enforceable."
            />

            <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_320px]">
                <div className="flex flex-col gap-5">
                    <ProfileIdentity profile={profile} />

                    {/* EXPERIENCE */}
                    <Panel>
                        <PanelHeader>
                            <Briefcase className="size-[16px] text-primary" />
                            <PanelTitle>Work experience</PanelTitle>
                            <Badge variant="soft">{experience.length}</Badge>
                            <span className="grow" />
                            <button className="inline-flex items-center gap-1.5 text-[13px] font-medium text-primary hover:underline">
                                <Plus className="size-[14px] " />
                                Add role
                            </button>
                        </PanelHeader>
                        <div>
                            {experience.map((job, i) => (
                                <div
                                    key={job.id}
                                    className={cn("px-5 py-5", i < experience.length - 1 && "border-b border-border")}
                                >
                                    <div className="flex flex-wrap items-start gap-4">
                                        <span className="grid size-11 shrink-0 place-items-center rounded-md bg-secondary text-muted-foreground">
                                            <Building2 className="size-[18px]" />
                                        </span>
                                        <div className="min-w-0 grow">
                                            <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                                                <h3 className="text-[15.5px] font-medium">{job.title}</h3>
                                                {job.current ? <Badge variant="soft">current</Badge> : null}
                                            </div>
                                            <p className="mt-1 text-[13.5px] text-muted-foreground">
                                                {job.company} · {job.location}
                                            </p>
                                            <p className="mt-0.5 text-[12.5px] text-muted-foreground">
                                                {job.start} — {job.end}
                                            </p>
                                            <ul className="mt-3 flex flex-col gap-2">
                                                {job.bullets.map((b) => (
                                                    <li key={b} className="flex gap-2.5 text-[13.5px] leading-relaxed">
                                                        <span className="mt-[7px] size-1.5 shrink-0 rounded-full bg-primary" />
                                                        <span className="text-muted-foreground">{b}</span>
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                        <Button variant="ghost" size="sm" className="shrink-0">
                                            <Pencil />
                                            Edit
                                        </Button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </Panel>

                    {/* EDUCATION */}
                    <Panel>
                        <PanelHeader>
                            <GraduationCap className="size-[16px] text-primary" />
                            <PanelTitle>Education</PanelTitle>
                            <span className="grow" />
                            <button className="inline-flex items-center gap-1.5 text-[13px] font-medium text-primary hover:underline">
                                <Plus className="size-[14px]" />
                                Add
                            </button>
                        </PanelHeader>
                        <div>
                            {education.map((e, i) => (
                                <div
                                    key={e.id}
                                    className={cn(
                                        "flex flex-wrap items-start gap-4 px-5 py-5",
                                        i < education.length - 1 && "border-b border-border"
                                    )}
                                >
                                    <span className="grid size-11 shrink-0 place-items-center rounded-md bg-secondary text-muted-foreground">
                                        <GraduationCap className="size-[18px]" />
                                    </span>
                                    <div className="min-w-0 grow">
                                        <h3 className="text-[15.5px] font-medium">{e.degree}</h3>
                                        <p className="mt-1 text-[13.5px] text-muted-foreground">
                                            {e.institution} · {e.location}
                                        </p>
                                        <p className="mt-0.5 text-[12.5px] text-muted-foreground">
                                            {e.start} — {e.end}
                                            {e.note ? ` · ${e.note}` : ""}
                                        </p>
                                    </div>
                                    <Button variant="ghost" size="sm" className="shrink-0">
                                        <Pencil />
                                        Edit
                                    </Button>
                                </div>
                            ))}
                        </div>
                    </Panel>

                    {/* SKILLS */}
                    <Panel>
                        <PanelHeader>
                            <Layers className="size-[16px] text-primary" />
                            <PanelTitle>Skills</PanelTitle>
                            <Badge variant="soft">{totalSkills}</Badge>
                            <span className="grow" />
                            <span className="text-[12.5px] text-muted-foreground">
                                grouped as in your .tex template
                            </span>
                        </PanelHeader>
                        <div>
                            {skillGroups.map((g, i) => (
                                <div
                                    key={g.name}
                                    className={cn(
                                        "flex flex-wrap items-start gap-x-5 gap-y-3 px-5 py-4",
                                        i < skillGroups.length - 1 && "border-b border-border"
                                    )}
                                >
                                    <p className="w-[118px] shrink-0 pt-1 text-[13px] font-medium">{g.name}</p>
                                    <div className="flex flex-wrap gap-2">
                                        {g.items.map((s) => (
                                            <span
                                                key={s}
                                                className="inline-flex items-center gap-2 rounded-sm bg-primary-tint px-2.5 py-1.5 text-[13px] text-accent-foreground"
                                            >
                                                {s}
                                                <span className="cursor-pointer text-[15px] leading-none opacity-45 hover:opacity-100">
                                                    ×
                                                </span>
                                            </span>
                                        ))}
                                        <span className="inline-flex cursor-pointer items-center rounded-sm border border-dashed border-border px-2.5 py-1.5 text-[13px] text-muted-foreground hover:border-primary hover:text-primary">
                                            + add
                                        </span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </Panel>

                    {/* CERTIFICATIONS */}
                    <Panel>
                        <PanelHeader>
                            <Award className="size-[16px] text-primary" />
                            <PanelTitle>Certifications</PanelTitle>
                            <Badge variant="soft">{certifications.length}</Badge>
                            <span className="grow" />
                            <button className="inline-flex items-center gap-1.5 text-[13px] font-medium text-primary hover:underline">
                                <Plus className="size-[14px]" />
                                Add
                            </button>
                        </PanelHeader>
                        <div className="grid sm:grid-cols-2">
                            {certifications.map((c, i) => (
                                <div
                                    key={c.id}
                                    className={cn(
                                        "flex items-start gap-3 px-5 py-4",
                                        i < certifications.length - (certifications.length % 2 === 0 ? 2 : 1) &&
                                        "border-b border-border",
                                        i % 2 === 0 && "sm:border-r sm:border-border"
                                    )}
                                >
                                    <Award className="mt-0.5 size-[15px] shrink-0 text-muted-foreground" />
                                    <div className="min-w-0">
                                        <p className="text-[13.5px] font-medium leading-snug">{c.name}</p>
                                        <p className="mt-1 text-[12.5px] text-muted-foreground">
                                            {c.issuer} · {c.year}
                                        </p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </Panel>
                </div>

                {/* rail */}
                <div className="flex flex-col gap-5">
                    <Panel>
                        <PanelHeader><PanelTitle>Indexed for retrieval</PanelTitle></PanelHeader>
                        <PanelBody className="flex flex-col gap-4 py-4">
                            <div className="grid grid-cols-2 gap-3">
                                <Stat n={profile.chunks} label="chunks" />
                                <Stat n={totalSkills} label="skills" />
                                <Stat n={experience.length} label="roles" />
                                <Stat n={certifications.length} label="certs" />
                            </div>
                            <p className="text-[12.5px] leading-relaxed text-muted-foreground">
                                Everything above is chunked and embedded so the match agent can find it. Editing a
                                section marks it for re-indexing.
                            </p>
                            <Button variant="outline" size="sm" className="w-full">
                                <RefreshCw />
                                Re-index now
                            </Button>
                            <p className="text-center text-[12px] text-muted-foreground">
                                last indexed {profile.lastIndexed}
                            </p>
                        </PanelBody>
                    </Panel>

                    <Panel>
                        <PanelHeader><PanelTitle>Resume template</PanelTitle></PanelHeader>
                        <PanelBody className="flex flex-col gap-3 py-4">
                            <div className="flex items-center gap-2.5 rounded-sm bg-well px-3 py-2.5">
                                <FileText className="size-[14px] shrink-0 text-muted-foreground" />
                                <span className="truncate font-mono text-[12px]">{profile.resumeFile}</span>
                            </div>
                            <p className="text-[12.5px] leading-relaxed text-muted-foreground">
                                Tailored resumes render this template with the sections above. The section names
                                here match its LaTeX commands, so what you see is what can be placed.
                            </p>
                        </PanelBody>
                    </Panel>

                    <Panel>
                        <PanelBody className="flex flex-col gap-3 py-4">
                            <p className="text-[13px] font-medium">Looking for something else?</p>
                            <Row icon={MapPin}>Target roles and locations are in Settings</Row>
                            <Row icon={Building2}>Company preference is in Settings</Row>
                            <Row icon={Mail}>Screening-question answers live with the extension</Row>
                        </PanelBody>
                    </Panel>
                </div>
            </div>
        </AppShell>
    );
}

function Stat({ n, label }) {
    return (
        <div className="rounded-sm bg-well px-3.5 py-3">
            <div className="text-[21px] font-bold leading-none">{n}</div>
            <div className="mt-1.5 text-[12px] text-muted-foreground">{label}</div>
        </div>
    );
}

function Row({ icon: Icon, children }) {
    return (
        <div className="flex items-start gap-2.5">
            <Icon className="mt-0.5 size-[13px] shrink-0 text-muted-foreground" />
            <span className="text-[12.5px] leading-relaxed text-muted-foreground">{children}</span>
        </div>
    );
}
