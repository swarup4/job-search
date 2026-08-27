import { getPendingCounts } from "./match";
import { listApplications } from "./application";
import { listJobs } from "./job";

const EMPTY = { pending: 0, shortlisted: 0 };

/**
 * The two badges AppShell renders on every screen. There is no aggregate endpoint
 * for them, so the client composes: keyword selections awaiting review plus
 * applications staged for submit, and the shortlist count.
 *
 * Chrome must not take a screen down — if the API is unreachable the badges read
 * zero and the page still renders. This is the one place a fallback is right,
 * because the numbers are decoration; everywhere else an error should surface.
 */
export async function getShellCounts() {
    try {
        const [pending, staged, shortlisted] = await Promise.all([
            getPendingCounts(),
            listApplications("staged"),
            listJobs({ shortlisted: true, limit: 200 }),
        ]);
        return {
            pending: pending.keyword_selections + staged.length,
            shortlisted: shortlisted.length,
        };
    } catch {
        return EMPTY;
    }
}
