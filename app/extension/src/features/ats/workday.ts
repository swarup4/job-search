import { firstFileInput, type AtsAdapter } from "@/features/ats/types";

/**
 * Workday names every control with `data-automation-id`, which makes it the most
 * stable of the four to target and the least pleasant to fill: the form is a
 * multi-step wizard, so one pass answers only the step on screen.
 */
export const workday: AtsAdapter = {
    platform: "workday",

    matches(url) {
        return /myworkdayjobs\.com$|myworkdaysite\.com$/.test(url.hostname);
    },

    root(doc) {
        return (
            doc.querySelector("[data-automation-id='applyFlowPage']") ??
            doc.querySelector("form") ??
            doc.body
        );
    },

    blocked(doc) {
        // A password box means the tenant's sign-in wall, not the application.
        const signIn = doc.querySelector(
            "[data-automation-id='password'], [data-automation-id='signInSubmitButton']",
        );
        return signIn ? "Sign in to Workday first — the application form is behind it." : null;
    },

    resumeInput(doc) {
        return (
            doc.querySelector<HTMLInputElement>("input[data-automation-id='file-upload-input-ref']") ??
            firstFileInput(doc)
        );
    },
};
