import { AppShell } from "@/layout/AppShell";
import { PageHeader } from "@/layout/PageHeader";
import { ResumeReview } from "@/component/ResumeReview";
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
        // The sidebar stays on Resume: this is that section, one step in.
        <AppShell active={ROUTES.resume} counts={counts}>
            <PageHeader
                title="Your resume"
                subtitle="The document every tailored version starts from. Regenerate it after editing My details, or ask the model to rectify it."
            />

            <ResumeReview />
        </AppShell>
    );
}
