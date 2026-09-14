import { AppShell } from "@/layout/AppShell";
import { PageHeader } from "@/layout/PageHeader";
import { ResumeBuilder } from "@/component/ResumeBuilder";
import { ROUTES } from "@/routes";
// MOCK: the shell badges still read fixtures — those endpoints are Phase 3/4 work.
import board from "@/data/board.json";
import search from "@/data/search.json";

export const dynamic = "force-dynamic";

export default function Page() {
    const counts = {
        pending: board.pending.keywordSelections + board.pending.applicationsToSubmit,
        shortlisted: search.shortlistedCount,
    };

    return (
        <AppShell active={ROUTES.resume} counts={counts}>
            <PageHeader
                title="Resume"
                subtitle="Your generic resume. Pick a template and submit it — your details are rendered into it, and every tailored version starts from the result. You review the document on the next screen."
            />

            <ResumeBuilder />
        </AppShell>
    );
}
