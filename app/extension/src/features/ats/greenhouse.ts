import { firstFileInput, type AtsAdapter } from "@/features/ats/types";

/**
 * Greenhouse embeds itself in the employer's own page as often as it serves its
 * own, so the iframe case is the normal one — the content script runs in every
 * frame and this adapter answers for whichever frame holds the form.
 */
export const greenhouse: AtsAdapter = {
    platform: "greenhouse",

    matches(url, doc) {
        if (/greenhouse\.io$/.test(url.hostname)) return true;
        return doc.querySelector("#grnhse_app, #application_form, form#application-form") !== null;
    },

    root(doc) {
        return (
            doc.querySelector(
                "#application_form, form#application-form, #grnhse_app, [data-testid='application-form']",
            ) ?? doc.querySelector("main")
        );
    },

    resumeInput(doc) {
        return (
            doc.querySelector<HTMLInputElement>("input#resume[type='file']") ??
            doc.querySelector<HTMLInputElement>("input[type='file'][name*='resume' i]") ??
            firstFileInput(doc)
        );
    },
};
