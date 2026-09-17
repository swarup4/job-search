import type { AtsAdapter } from "@/features/ats/types";

const MODAL = ".jobs-easy-apply-modal, [data-test-modal], .jobs-easy-apply-content";

/**
 * Easy Apply lives in a modal over the job page, so there is nothing to fill
 * until the user opens it. The resume step offers files already uploaded to
 * LinkedIn rather than a file input, which is why `resumeInput` is absent.
 */
export const linkedin: AtsAdapter = {
    platform: "linkedin_easy_apply",

    matches(url) {
        return url.hostname.endsWith("linkedin.com");
    },

    root(doc) {
        return doc.querySelector(MODAL);
    },

    blocked(doc) {
        return doc.querySelector(MODAL) ? null : "Click Easy Apply first, then fill.";
    },
};
