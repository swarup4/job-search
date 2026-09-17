/** FR-5.2 — turning a control into the question it is actually asking. */

const NOISE = /\s*(\*+|\(required\)|\(optional\)|required|optional)\s*$/gi;

const CONTROLS = "input:not([type='hidden']), select, textarea, [role='combobox']";

/** Comparison form: lowercased, punctuation flattened, one space between words. */
export function normalize(text: string): string {
    return text
        .replace(/[‘’]/g, "'")
        .replace(NOISE, "")
        .toLowerCase()
        .replace(/[^a-z0-9'+/\s-]/g, " ")
        .replace(/\s+/g, " ")
        .trim();
}

/** `firstName`, `first_name`, `urls[LinkedIn]` → `first name`, `urls linkedin`. */
export function humanize(token: string): string {
    return token
        .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
        .replace(/[-_.[\]]+/g, " ")
        .replace(/\s+/g, " ")
        .trim();
}

function textOf(el: Element | null): string {
    if (!el) return "";
    return (el.textContent ?? "").replace(/\s+/g, " ").trim();
}

function byId(doc: Document, id: string): Element | null {
    try {
        return doc.querySelector(`#${CSS.escape(id)}`);
    } catch {
        return null;
    }
}

/** A wrapping <label> includes the control's own text (option names, button
 * captions). Strip the controls out before reading it. */
function textOfLabel(label: Element): string {
    const copy = label.cloneNode(true) as Element;
    copy.querySelectorAll("input, select, textarea, button, [role='button']").forEach((node) =>
        node.remove(),
    );
    return textOf(copy);
}

/** The label a human sees above this control, or "" when there is none. */
export function labelFor(el: Element): string {
    const doc = el.ownerDocument;

    const labelledBy = el.getAttribute("aria-labelledby");
    if (labelledBy) {
        const joined = labelledBy
            .split(/\s+/)
            .map((id) => textOf(byId(doc, id)))
            .filter(Boolean)
            .join(" ");
        if (joined) return joined;
    }

    if (el.id) {
        const explicit = doc.querySelector(`label[for="${CSS.escape(el.id)}"]`);
        if (explicit) {
            const text = textOfLabel(explicit);
            if (text) return text;
        }
    }

    const wrapping = el.closest("label");
    if (wrapping) {
        const text = textOfLabel(wrapping);
        if (text) return text;
    }

    const aria = el.getAttribute("aria-label");
    if (aria?.trim()) return aria.trim();

    // A radio or checkbox is labelled by its group, not by itself.
    const group = el.closest("fieldset, [role='group'], [role='radiogroup']");
    const legend = group?.querySelector("legend, [role='heading']");
    if (legend) {
        const text = textOf(legend);
        if (text) return text;
    }

    const nearby = nearbyLabel(el);
    if (nearby) return nearby;

    const placeholder = el.getAttribute("placeholder");
    if (placeholder?.trim()) return placeholder.trim();

    // Workday names every control; the name is the question, spelled in camelCase.
    const automation = el.getAttribute("data-automation-id") ?? el.getAttribute("data-testid");
    if (automation) return humanize(automation);

    const name = el.getAttribute("name") ?? el.id;
    return name ? humanize(name) : "";
}

/**
 * Climb a few wrappers looking for the label text sitting beside the control —
 * the shape most component libraries produce when they skip `for`.
 *
 * A wrapper holding more than one control is not trusted: its label belongs to
 * whichever control comes first, and borrowing it would put the question from one
 * field onto another.
 */
function nearbyLabel(el: Element): string {
    let node: Element | null = el;

    for (let depth = 0; node && depth < 4; depth += 1) {
        const parent: Element | null = node.parentElement;
        if (!parent) return "";

        if (parent.querySelectorAll(CONTROLS).length > 1) return "";

        const candidate = parent.querySelector("label, legend, [class*='label' i]");
        if (candidate && !candidate.contains(el)) {
            const text = textOfLabel(candidate);
            if (text) return text;
        }

        node = parent;
    }

    return "";
}

/**
 * The question a set of radios is asking, which is never the wrapping label —
 * that one holds a single option's text ("Yes"). It comes from the fieldset,
 * the radiogroup, or whichever wrapper first contains the whole group.
 */
export function labelForRadioGroup(group: HTMLInputElement[]): string {
    const first = group[0];
    if (!first) return "";

    let scope: Element | null = first.closest("fieldset, [role='radiogroup'], [role='group']");
    if (!scope) {
        scope = first.parentElement;
        while (scope && !group.every((radio) => scope!.contains(radio))) scope = scope.parentElement;
    }
    if (!scope) return "";

    const labelledBy = scope.getAttribute("aria-labelledby");
    if (labelledBy) {
        const doc = first.ownerDocument;
        const joined = labelledBy
            .split(/\s+/)
            .map((id) => textOf(byId(doc, id)))
            .filter(Boolean)
            .join(" ");
        if (joined) return joined;
    }

    const aria = scope.getAttribute("aria-label");
    if (aria?.trim()) return aria.trim();

    const candidates = scope.querySelectorAll("legend, [role='heading'], [class*='label' i], label");
    for (const candidate of candidates) {
        if (group.some((radio) => candidate.contains(radio))) continue;
        const text = textOfLabel(candidate);
        if (text) return text;
    }

    return "";
}
