import { axiosInstance } from "@/lib/axiosInstance";

/**
 * GET /api/status — every number the dashboard shows outside a page's own list, in one
 * read: `badges` (header, sidebar, review banner), `pipeline` (column totals), `jobs`
 * (total, unscored, analyzed), `discovery` (the last run), `profile` (index, default
 * resume) and `serverTime`.
 *
 * Chrome must not take a screen down — if the API is unreachable this answers null, the
 * store keeps its last numbers and the page still renders. This is the one place a
 * fallback is right, because the numbers are decoration; everywhere else an error
 * should surface.
 */
export async function getStatus() {
    try {
        return await axiosInstance.get("/status");
    } catch {
        return null;
    }
}
