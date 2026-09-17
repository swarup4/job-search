import type { ScannedField } from "@/features/fieldFill/scan";
import type { AtsPlatform } from "@/shared/types";

/**
 * What one job board needs beyond the generic engine. Every hook is optional:
 * an adapter exists to correct the generic behaviour, not to replace it, so a
 * selector drifting out of date degrades to "generic engine only" rather than
 * to nothing working.
 */
export interface AtsAdapter {
    readonly platform: AtsPlatform;
    matches(url: URL, doc: Document): boolean;
    /** The application form, when the page holds other forms (search, login). */
    root?(doc: Document): ParentNode | null;
    /** Why the form cannot be filled yet, e.g. an unopened Easy Apply modal. */
    blocked?(doc: Document): string | null;
    resumeInput?(doc: Document): HTMLInputElement | null;
    /** Platform-specific widget handling. `null` falls through to the engine. */
    fill?(field: ScannedField, value: string): Promise<boolean | null>;
}

export function firstFileInput(root: ParentNode, pattern = /resume|cv|curriculum/i): HTMLInputElement | null {
    const inputs = Array.from(root.querySelectorAll<HTMLInputElement>("input[type='file']"));
    const named = inputs.find(
        (input) =>
            pattern.test(input.name) ||
            pattern.test(input.id) ||
            pattern.test(input.getAttribute("aria-label") ?? "") ||
            pattern.test(input.closest("[class], [data-testid]")?.className.toString() ?? ""),
    );
    return named ?? inputs[0] ?? null;
}
