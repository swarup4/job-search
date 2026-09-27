import { getBadges } from "./application";

/**
 * The badges AppShell renders on every screen, from one call. `pending` is the
 * Applications badge: keyword choices waiting plus applications staged for submit.
 *
 * Chrome must not take a screen down — if the API is unreachable this answers null,
 * the badges keep their last numbers and the page still renders. This is the one
 * place a fallback is right, because the numbers are decoration; everywhere else an
 * error should surface.
 */
export async function getShellCounts() {
    try {
        const badges = await getBadges();
        return { ...badges, pending: badges.keywordSelections + badges.staged };
    } catch {
        return null;
    }
}
