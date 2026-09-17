import { firstFileInput, type AtsAdapter } from "@/features/ats/types";

/** The simplest of the four: plain inputs, real names, one form. */
export const lever: AtsAdapter = {
    platform: "lever",

    matches(url) {
        return /(^|\.)lever\.co$/.test(url.hostname);
    },

    root(doc) {
        return doc.querySelector("form[action*='apply'], .application-form, #application-form");
    },

    resumeInput(doc) {
        return doc.querySelector<HTMLInputElement>("input[name='resume']") ?? firstFileInput(doc);
    },
};
