import { labelFor, labelForRadioGroup, normalize } from "@/features/fieldFill/label";
import { selectorFor } from "@/features/fieldFill/selector";

export type FieldKind =
    | "text"
    | "textarea"
    | "select"
    | "checkbox"
    | "radio"
    | "file"
    | "combobox"
    | "date";

export interface ScannedField {
    el: HTMLElement;
    /** Every radio in the group, so filling can click the right one. */
    group: HTMLInputElement[];
    kind: FieldKind;
    label: string;
    key: string;
    selector: string;
    options: string[];
    required: boolean;
    /** Already answered — by the page, the browser, or a previous fill. */
    prefilled: boolean;
}

const SKIP_TYPES = new Set(["hidden", "submit", "button", "reset", "image", "password"]);
const JUNK = /captcha|honeypot|^_|csrf|recaptcha/i;

/**
 * Deliberately style-based rather than geometry-based. A control that is 0x0 is
 * routinely a real one behind a styled stand-in — every file input is — so its
 * size says nothing, while `display` and `visibility` are what a wizard actually
 * uses to put a later step out of reach.
 */
function visible(el: HTMLElement): boolean {
    if (el.hasAttribute("hidden")) return false;
    if (el.closest("[aria-hidden='true'], details:not([open])")) return false;

    const style = getComputedStyle(el);
    return style.display !== "none" && style.visibility !== "hidden";
}

function kindOf(el: HTMLElement): FieldKind | null {
    if (el instanceof HTMLTextAreaElement) return "textarea";
    if (el instanceof HTMLSelectElement) return "select";

    if (el instanceof HTMLInputElement) {
        const type = el.type.toLowerCase();
        if (SKIP_TYPES.has(type)) return null;
        if (type === "file") return "file";
        if (type === "checkbox") return "checkbox";
        if (type === "radio") return "radio";
        if (type === "date" || type === "month") return "date";
        // A combobox input drives a listbox; typing into it is not enough.
        if (el.getAttribute("role") === "combobox" || el.getAttribute("aria-haspopup") === "listbox") {
            return "combobox";
        }
        return "text";
    }

    if (el.getAttribute("role") === "combobox" || el.getAttribute("aria-haspopup") === "listbox") {
        return "combobox";
    }
    if (el.isContentEditable) return "textarea";

    return null;
}

function optionsOf(el: HTMLElement, kind: FieldKind, group: HTMLInputElement[]): string[] {
    if (kind === "select" && el instanceof HTMLSelectElement) {
        return Array.from(el.options)
            .map((option) => option.text.trim())
            .filter(Boolean);
    }

    if (kind === "radio") return group.map((radio) => labelFor(radio)).filter(Boolean);

    if (kind === "combobox") {
        const listboxId = el.getAttribute("aria-controls") ?? el.getAttribute("aria-owns");
        const listbox = listboxId ? el.ownerDocument.getElementById(listboxId) : null;
        if (listbox) {
            return Array.from(listbox.querySelectorAll("[role='option']"))
                .map((option) => (option.textContent ?? "").trim())
                .filter(Boolean);
        }
    }

    return [];
}

function prefilledCheck(el: HTMLElement, kind: FieldKind, group: HTMLInputElement[]): boolean {
    if (kind === "radio") return group.some((radio) => radio.checked);
    if (kind === "checkbox") return (el as HTMLInputElement).checked;
    if (kind === "file") return ((el as HTMLInputElement).files?.length ?? 0) > 0;
    if (kind === "select") {
        const select = el as HTMLSelectElement;
        // An unset <select> usually rests on a blank or placeholder first option.
        return select.selectedIndex > 0 && select.value !== "";
    }
    if (el.isContentEditable) return (el.textContent ?? "").trim() !== "";
    return "value" in el && String((el as HTMLInputElement).value).trim() !== "";
}

/** Every control on this document worth trying to answer. */
export function scan(root: ParentNode = document): ScannedField[] {
    const candidates = root.querySelectorAll<HTMLElement>(
        "input, select, textarea, [role='combobox'], [aria-haspopup='listbox'], [contenteditable='true']",
    );

    const fields: ScannedField[] = [];
    const seenRadioGroups = new Set<string>();

    for (const el of candidates) {
        const kind = kindOf(el);
        if (!kind) continue;

        const name = el.getAttribute("name") ?? "";
        if (JUNK.test(name) || JUNK.test(el.id)) continue;
        if (kind !== "file" && !visible(el)) continue;
        if (el instanceof HTMLInputElement && (el.disabled || el.readOnly)) continue;
        if (el instanceof HTMLSelectElement && el.disabled) continue;

        let group: HTMLInputElement[] = [];
        if (kind === "radio" && el instanceof HTMLInputElement) {
            if (!name) continue;
            const scope: ParentNode = el.form ?? el.ownerDocument;
            if (seenRadioGroups.has(name)) continue;
            seenRadioGroups.add(name);
            group = Array.from(
                scope.querySelectorAll<HTMLInputElement>(
                    `input[type="radio"][name="${CSS.escape(name)}"]`,
                ),
            );
        }

        // A radio is labelled by its group; `labelFor` would return one option.
        const label = kind === "radio" ? labelForRadioGroup(group) || labelFor(el) : labelFor(el);
        if (!label) continue;

        fields.push({
            el,
            group,
            kind,
            label,
            key: normalize(label),
            selector: selectorFor(el),
            options: optionsOf(el, kind, group),
            required: el.getAttribute("aria-required") === "true" || el.hasAttribute("required"),
            prefilled: prefilledCheck(el, kind, group),
        });
    }

    return fields;
}
