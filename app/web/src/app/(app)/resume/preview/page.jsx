import { PageHeader } from "@/layout/PageHeader";
import { ResumeReview } from "@/component/ResumeReview";

export const dynamic = "force-dynamic";

export default function Page() {

    return (
        // The sidebar stays on Resume: this is that section, one step in.
        <>
            <PageHeader
                title="Your resume"
                subtitle="The document every tailored version starts from. Regenerate it after editing My details, or ask the model to rectify it."
            />

            <ResumeReview />
        </>
    );
}
