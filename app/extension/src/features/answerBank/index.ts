import { humanize, normalize } from "@/features/fieldFill/label";
import type { AnswerBankEntry } from "@/shared/types";

/** The user's own stored answers, looked up by the question a form is asking.
 * `usedCount` already sorts the list server-side, so the first acceptable match
 * is the one they reach for most. */

function tokens(text: string): Set<string> {
    return new Set(normalize(text).split(" ").filter((word) => word.length > 2));
}

function overlap(a: Set<string>, b: Set<string>): number {
    if (a.size === 0 || b.size === 0) return 0;
    let shared = 0;
    for (const word of a) if (b.has(word)) shared += 1;
    return shared / Math.min(a.size, b.size);
}

export interface BankMatch {
    entry: AnswerBankEntry;
    exact: boolean;
}

/**
 * `key` is matched first because the user chose it deliberately ("notice_period"
 * answers "What is your notice period?"). Question text is the fallback, and a
 * loose one — 0.75 of the shorter side's words, so "notice period" matches
 * "What is your notice period in days?" but not "What is your current salary?".
 */
export function lookup(
    entries: AnswerBankEntry[],
    fieldKey: string,
    canonicalKey: string | null,
): BankMatch | null {
    for (const entry of entries) {
        const entryKey = normalize(humanize(entry.key));
        if (canonicalKey && entryKey === normalize(humanize(canonicalKey))) {
            return { entry, exact: true };
        }
        if (entryKey === fieldKey || normalize(entry.question) === fieldKey) {
            return { entry, exact: true };
        }
    }

    const fieldTokens = tokens(fieldKey);
    let best: BankMatch | null = null;
    let bestScore = 0.75;

    for (const entry of entries) {
        const score = Math.max(
            overlap(fieldTokens, tokens(entry.question)),
            overlap(fieldTokens, tokens(humanize(entry.key))),
        );
        if (score > bestScore) {
            best = { entry, exact: false };
            bestScore = score;
        }
    }

    return best;
}
