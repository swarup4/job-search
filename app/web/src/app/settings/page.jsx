import {
    Ban, Building2, Database, Save, ShieldCheck, Sparkles, Star, Table2,
} from "lucide-react";
import { AppShell } from "@/layout/AppShell";
import { PageHeader } from "@/layout/PageHeader";
import { SettingRow } from "@/component/SettingRow";
import { Panel, PanelBody, PanelHeader, PanelTitle } from "@/component/ui/panel";
import { Field, Input, TokenList } from "@/component/ui/field";
import { Toggle } from "@/component/ui/toggle";
import { Badge } from "@/component/ui/badge";
import { Button } from "@/component/ui/button";
import { ROUTES } from "@/routes";
import settings from "@/data/settings.json";
import board from "@/data/board.json";
import search from "@/data/search.json";
import { cn } from "@/util/cn";

export default function Page() {
    const { targets, companyPreference: cp, discovery, applications, ai } = settings;

    return (
        <AppShell
            active={ROUTES.settings}
            counts={{
        pending: board.pending.keywordSelections + board.pending.applicationsToSubmit,
        shortlisted: search.shortlistedCount,
      }}
        >
            <PageHeader
                title="Settings"
                subtitle="What the agents look for, which companies you care about, and how far they may go without you."
            >
                <Button size="sm">
                    <Save />
                    Save changes
                </Button>
            </PageHeader>

            <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_340px]">
                <div className="flex flex-col gap-5">
                    {/* COMPANY PREFERENCE */}
                    <Panel>
                        <PanelHeader>
                            <Building2 className="size-[16px] text-primary" />
                            <PanelTitle>Company preference</PanelTitle>
                        </PanelHeader>
                        <PanelBody className="flex flex-col gap-6 py-5">
                            <Field
                                label="Preferred companies"
                                hint="Matches from these are surfaced first, and never hidden by the minimum-match cutoff."
                            >
                                <TokenList items={cp.preferred} />
                            </Field>

                            <Field
                                label="Excluded companies"
                                hint="Discovery drops these before scoring, so they never reach your shortlist."
                            >
                                <TokenList items={cp.excluded} tone="muted" />
                            </Field>

                            <Field label="Company size" hint="Headcount bands worth your time.">
                                <div className="flex flex-wrap gap-2">
                                    {cp.sizes.map((s) => (
                                        <span
                                            key={s.label}
                                            className={cn(
                                                "cursor-pointer rounded-sm px-3 py-1.5 text-[13px] transition-colors",
                                                s.on
                                                    ? "bg-primary text-primary-foreground"
                                                    : "bg-secondary text-muted-foreground hover:text-foreground"
                                            )}
                                        >
                                            {s.label}
                                        </span>
                                    ))}
                                </div>
                            </Field>

                            <Field label="Industries" hint="Used as a scoring signal, not a hard filter.">
                                <TokenList items={cp.industries} />
                            </Field>
                        </PanelBody>
                        <SettingRow
                            label="Skip staffing and consultancy firms"
                            hint="Filters out listings whose hiring company is an agency rather than the employer."
                            last
                        >
                            <Toggle defaultOn={cp.avoidStaffing} />
                        </SettingRow>
                    </Panel>

                    {/* SEARCH TARGETS */}
                    <Panel>
                        <PanelHeader>
                            <Star className="size-[16px] text-primary" />
                            <PanelTitle>Search targets</PanelTitle>
                        </PanelHeader>
                        <PanelBody className="flex flex-col gap-6 py-5">
                            <Field label="Target roles" hint="Drives the daily discovery run across every enabled source.">
                                <TokenList items={targets.roles} />
                            </Field>
                            <Field label="Locations" hint={targets.workMode}>
                                <TokenList items={targets.locations} tone="muted" />
                            </Field>
                            <div className="grid gap-5 sm:grid-cols-3">
                                <Field label="Min experience (yrs)">
                                    <Input defaultValue={targets.minExperience} />
                                </Field>
                                <Field label="Max experience (yrs)">
                                    <Input defaultValue={targets.maxExperience} />
                                </Field>
                                <Field label="Minimum salary">
                                    <Input defaultValue={targets.minSalary} />
                                </Field>
                            </div>
                        </PanelBody>
                    </Panel>

                    {/* DISCOVERY */}
                    <Panel>
                        <PanelHeader>
                            <Sparkles className="size-[16px] text-primary" />
                            <PanelTitle>Discovery</PanelTitle>
                        </PanelHeader>
                        <PanelBody className="grid gap-5 py-5 sm:grid-cols-2">
                            <Field label="Schedule">
                                <Input defaultValue={discovery.schedule} />
                            </Field>
                            <Field label="Minimum match to shortlist" hint="Below this, a job is stored but not surfaced.">
                                <Input defaultValue={discovery.minMatch} />
                            </Field>
                        </PanelBody>
                        <SettingRow
                            label="Deduplicate by content hash"
                            hint="The same posting often appears on several boards. Off means you review it more than once."
                        >
                            <Toggle defaultOn={discovery.dedupe} />
                        </SettingRow>
                        <SettingRow
                            label="Respect robots.txt and rate limits"
                            hint="Required for the scraped sources. Turning this off is not supported."
                            last
                        >
                            <Toggle defaultOn={discovery.respectRobots} disabled />
                        </SettingRow>
                    </Panel>

                    {/* APPLICATIONS */}
                    <Panel>
                        <PanelHeader>
                            <Table2 className="size-[16px] text-primary" />
                            <PanelTitle>Applications</PanelTitle>
                        </PanelHeader>
                        <PanelBody className="grid gap-5 py-5 sm:grid-cols-2">
                            <Field label="Follow-up reminder after (days)">
                                <Input defaultValue={applications.followUpDays} />
                            </Field>
                            <Field label="Google Sheet">
                                <Input defaultValue={applications.sheetName} />
                            </Field>
                        </PanelBody>
                        <SettingRow label="Sync status to Google Sheet" hint="One-way push whenever a status changes.">
                            <Toggle defaultOn={applications.sheetSync} />
                        </SettingRow>
                        <SettingRow
                            label="Auto-submit applications"
                            hint="Permanently unavailable. The extension fills forms and stops; ATS terms of service require a human to submit, and there is no code path that does it for you."
                            last
                        >
                            <div className="flex items-center gap-3">
                                <Badge variant="risk">not available</Badge>
                                <Toggle defaultOn={false} disabled />
                            </div>
                        </SettingRow>
                    </Panel>
                </div>

                {/* rail */}
                <div className="flex flex-col gap-5">
                    <Panel>
                        <PanelHeader><PanelTitle>Sources</PanelTitle></PanelHeader>
                        <div>
                            {discovery.sources.map((s, i) => (
                                <div
                                    key={s.name}
                                    className={cn(
                                        "flex items-center gap-3 px-5 py-3.5",
                                        i < discovery.sources.length - 1 && "border-b border-border"
                                    )}
                                >
                                    <div className="min-w-0 grow">
                                        <p className="truncate text-[14px]">{s.name}</p>
                                        <p className="mt-0.5 text-[12px] text-muted-foreground">
                                            {s.on ? `${s.found} found in 30 days` : "disabled"}
                                        </p>
                                    </div>
                                    <Toggle defaultOn={s.on} />
                                </div>
                            ))}
                        </div>
                    </Panel>

                    <Panel>
                        <PanelHeader>
                            <ShieldCheck className="size-[16px] text-primary" />
                            <PanelTitle>Models &amp; privacy</PanelTitle>
                        </PanelHeader>
                        <PanelBody className="flex flex-col gap-4 py-4">
                            <KV label="Generation" value={ai.llm} note="local" />
                            <KV label="Host" value={ai.llmHost} />
                            <KV label="Embeddings" value={ai.embedModel} note="hosted" warn />
                            <KV label="Eval judge" value={ai.judge} note="local" />
                            <div className="flex items-center justify-between gap-3 border-t border-border pt-4">
                                <span className="text-[13px]">Rerank retrieved chunks</span>
                                <Toggle defaultOn={ai.rerank} />
                            </div>
                            <p className="text-[12.5px] leading-relaxed text-muted-foreground">
                                All generation runs on your machine. Chunk text and JDs are sent to the embedding
                                provider; Atlas stores vectors and identifiers only, never resume prose.
                            </p>
                        </PanelBody>
                    </Panel>

                    <Panel>
                        <PanelHeader>
                            <Database className="size-[16px] text-primary" />
                            <PanelTitle>Stores</PanelTitle>
                        </PanelHeader>
                        <PanelBody className="flex flex-col gap-3 py-4">
                            <KV label="Structural" value="Local MongoDB" />
                            <KV label="Vectors" value="MongoDB Atlas" />
                            <KV label="Queue" value="Redis" />
                        </PanelBody>
                    </Panel>

                    <Panel>
                        <PanelBody className="flex items-start gap-3 py-4">
                            <Ban className="mt-0.5 size-[15px] shrink-0 text-muted-foreground" />
                            <p className="text-[12.5px] leading-relaxed text-muted-foreground">
                                Single-user by design — there is no account, no login, and nothing to share.
                                Everything here lives on this machine.
                            </p>
                        </PanelBody>
                    </Panel>
                </div>
            </div>
        </AppShell>
    );
}

function KV({ label, value, note, warn }) {
    return (
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <span className="text-[12.5px] text-muted-foreground">{label}</span>
            <span className="grow" />
            <span className="font-mono text-[12.5px]">{value}</span>
            {note ? (
                <Badge variant={warn ? "attention" : "soft"} className="ml-1">{note}</Badge>
            ) : null}
        </div>
    );
}
