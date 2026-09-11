import { Building2, FileText, Mail, MapPin, RefreshCw } from "lucide-react";
import { AppShell } from "@/layout/AppShell";
import { PageHeader } from "@/layout/PageHeader";
import { Panel, PanelBody, PanelHeader, PanelTitle } from "@/component/ui/panel";
import { Button } from "@/component/ui/button";
import { ROUTES } from "@/routes";
// MOCK: live data is off while demoing the UI — restore this import and the call below.
// import { getProfile, getShellCounts } from "@/services";
import profileData from "@/data/profile.json";
import board from "@/data/board.json";
import search from "@/data/search.json";
import { ProfileIdentity } from "@/component/ProfileIdentity";
import { EmptyProfile } from "@/component/EmptyProfile";
import { EducationSection } from "@/component/EducationSection";
import { ExperienceSection } from "@/component/ExperienceSection";
import { CertificationsSection } from "@/component/CertificationsSection";
import { SkillsSection } from "@/component/SkillsSection";
import { IndexedStats } from "@/component/IndexedStats";

export const dynamic = "force-dynamic";

export default async function Page() {
    // const [profile, counts] = await Promise.all([getProfile(), getShellCounts()]);
    // Only the retrieval panels read this now; everything editable lives in the store.
    const profile = profileData;
    const counts = {
        pending: board.pending.keywordSelections + board.pending.applicationsToSubmit,
        shortlisted: search.shortlistedCount,
    };

    if (!profile) {
        return (
            <AppShell active={ROUTES.profile} counts={counts}>
                <EmptyProfile />
            </AppShell>
        );
    }

    return (
        <AppShell active={ROUTES.profile} counts={counts}>
            <PageHeader
                title="My details"
                subtitle="Your resume material. Tailoring may only draw on what exists here — that constraint is what makes the no-fabrication rule enforceable."
            />

            <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_320px]">
                <div className="flex flex-col gap-5">
                    <ProfileIdentity />

                    <ExperienceSection />

                    <EducationSection />

                    <SkillsSection />

                    <CertificationsSection />
                </div>

                <div className="flex flex-col gap-5">
                    <Panel>
                        <PanelHeader><PanelTitle>Indexed for retrieval</PanelTitle></PanelHeader>
                        <PanelBody className="flex flex-col gap-4 py-4">
                            <IndexedStats chunks={profile.chunks} />
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

function Row({ icon: Icon, children }) {
    return (
        <div className="flex items-start gap-2.5">
            <Icon className="mt-0.5 size-[13px] shrink-0 text-muted-foreground" />
            <span className="text-[12.5px] leading-relaxed text-muted-foreground">{children}</span>
        </div>
    );
}
