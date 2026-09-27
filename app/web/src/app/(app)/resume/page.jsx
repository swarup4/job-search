import { PageHeader } from "@/layout/PageHeader";
import { ResumeBuilder } from "@/component/ResumeBuilder";

export const dynamic = "force-dynamic";

export default function Page() {

    return (
        <>
            <PageHeader
                title="Resume"
                subtitle="Your generic resume. Pick a template and submit it — your details are rendered into it, and every tailored version starts from the result. You review the document on the next screen."
            />

            <ResumeBuilder />
        </>
    );
}
