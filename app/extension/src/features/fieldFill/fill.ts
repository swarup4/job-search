import { labelFor, normalize } from "@/features/fieldFill/label";
import type { ScannedField } from "@/features/fieldFill/scan";

/**
 * Setting `.value` directly does nothing durable on a React form: the property is
 * shadowed by React's own descriptor, so the assignment never reaches the
 * component and the next render restores the old value. Going through the
 * prototype's native setter, then dispatching the event React listens for, is
 * what makes a programmatic fill survive. Every ATS here is React.
 */
function setNativeValue(el: HTMLElement, value: string): void {
    const proto =
        el instanceof HTMLTextAreaElement
            ? HTMLTextAreaElement.prototype
            : el instanceof HTMLSelectElement
              ? HTMLSelectElement.prototype
              : HTMLInputElement.prototype;

    const setter = Object.getOwnPropertyDescriptor(proto, "value")?.set;
    if (setter) setter.call(el, value);
    else (el as HTMLInputElement).value = value;
}

function dispatch(el: HTMLElement, ...names: string[]): void {
    for (const name of names) {
        el.dispatchEvent(new Event(name, { bubbles: true, composed: true }));
    }
}

const TRUTHY = new Set(["yes", "true", "y", "1", "on", "agree", "i agree", "accept", "checked"]);
const FALSY = new Set(["no", "false", "n", "0", "off", "decline", "disagree"]);

/** "true" and "Yes" are the same answer to a yes/no question. */
function canonicalAnswer(value: string): string {
    const clean = normalize(value);
    if (TRUTHY.has(clean)) return "yes";
    if (FALSY.has(clean)) return "no";
    return clean;
}

/** Exact, then prefix, then substring — never a partial-word coincidence. */
function bestOption(options: string[], value: string): number | null {
    const wanted = canonicalAnswer(value);
    const normalized = options.map((option) => canonicalAnswer(option));

    const exact = normalized.indexOf(wanted);
    if (exact >= 0) return exact;

    const prefix = normalized.findIndex(
        (option) => option.startsWith(wanted) || wanted.startsWith(option),
    );
    if (prefix >= 0 && wanted.length > 1) return prefix;

    if (wanted.length > 2) {
        const partial = normalized.findIndex(
            (option) => option.includes(wanted) || wanted.includes(option),
        );
        if (partial >= 0) return partial;
    }

    return null;
}

function wait(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitFor<T>(probe: () => T | null, timeout = 1200): Promise<T | null> {
    const deadline = Date.now() + timeout;
    while (Date.now() < deadline) {
        const found = probe();
        if (found) return found;
        await wait(50);
    }
    return null;
}

function fillText(el: HTMLElement, value: string): boolean {
    if (el.isContentEditable) {
        el.focus();
        el.textContent = value;
        dispatch(el, "input", "change");
        return true;
    }

    el.focus();
    setNativeValue(el, value);
    dispatch(el, "input", "change");
    el.blur();
    return true;
}

function fillSelect(el: HTMLSelectElement, value: string): boolean {
    const texts = Array.from(el.options).map((option) => option.text);
    const index = bestOption(texts, value);
    if (index === null) return false;

    const option = el.options[index];
    if (!option) return false;

    el.focus();
    setNativeValue(el, option.value);
    dispatch(el, "input", "change");
    el.blur();
    return true;
}

function fillRadio(group: HTMLInputElement[], value: string): boolean {
    const labels = group.map((radio) => labelFor(radio) || radio.value);
    const index = bestOption(labels, value);
    if (index === null) return false;

    const radio = group[index];
    if (!radio) return false;

    // A click, not `.checked = true`: the click is what the page's handler sees.
    radio.click();
    return radio.checked;
}

function fillCheckbox(el: HTMLInputElement, value: string): boolean {
    const wanted = canonicalAnswer(value);
    if (wanted !== "yes" && wanted !== "no") return false;

    const shouldCheck = wanted === "yes";
    if (el.checked !== shouldCheck) el.click();
    return el.checked === shouldCheck;
}

/** Workday calls its options `promptOption`; everyone else uses the ARIA role. */
const OPTION = "[role='option'], [data-automation-id='promptOption']";

/**
 * Deliberately not `offsetParent`, which is null for any `position: fixed`
 * element — and an ATS dropdown is a fixed-position popup. Testing offsetParent
 * rejected every real listbox on Workday and Greenhouse.
 */
function onScreen(el: HTMLElement): boolean {
    if (el.getClientRects().length > 0) return true;
    const style = getComputedStyle(el);
    return style.display !== "none" && style.visibility !== "hidden";
}

/**
 * The options an open combobox is offering. `aria-controls` names them when the
 * widget bothers to set it; when it does not, they are looked up document-wide,
 * because Workday and Greenhouse both render the popup at the end of `<body>`
 * rather than inside the control that owns it.
 */
function openOptions(el: HTMLElement): HTMLElement[] {
    const doc = el.ownerDocument;
    const id = el.getAttribute("aria-controls") ?? el.getAttribute("aria-owns");
    const named = id ? doc.getElementById(id) : null;

    const scoped = named ? Array.from(named.querySelectorAll<HTMLElement>(OPTION)) : [];
    const visible = scoped.filter(onScreen);
    if (visible.length > 0) return visible;

    return Array.from(doc.querySelectorAll<HTMLElement>(OPTION)).filter(onScreen);
}

/**
 * The widget every modern ATS uses instead of `<select>`: an input or button that
 * opens a listbox. It has to be driven the way a person drives it — open, filter,
 * click — because there is no value to set.
 */
async function fillCombobox(el: HTMLElement, value: string): Promise<boolean> {
    el.focus();
    el.click();

    if (el instanceof HTMLInputElement) {
        setNativeValue(el, value);
        dispatch(el, "input");
    }

    const options = await waitFor(() => {
        const found = openOptions(el);
        return found.length > 0 ? found : null;
    });
    if (!options) return false;

    const index = bestOption(
        options.map((option) => (option.textContent ?? "").trim()),
        value,
    );
    if (index === null) {
        el.blur();
        return false;
    }

    const option = options[index];
    if (!option) return false;

    option.click();
    // Workday commits on selection; Greenhouse needs the input to settle first.
    await wait(80);
    return true;
}

/**
 * Contrary to the long-standing assumption, a file input *can* be set from a
 * content script: `FileList` is read-only but assignable from a `DataTransfer`.
 * That is what makes the resume attach automatic instead of a manual step.
 */
export function attachFile(
    input: HTMLInputElement,
    name: string,
    base64: string,
    type = "application/pdf",
): boolean {
    try {
        const binary = atob(base64);
        const bytes = new Uint8Array(binary.length);
        for (let index = 0; index < binary.length; index += 1) {
            bytes[index] = binary.charCodeAt(index);
        }

        const transfer = new DataTransfer();
        transfer.items.add(new File([bytes], name, { type }));
        input.files = transfer.files;
        dispatch(input, "input", "change");
        return input.files.length === 1;
    } catch {
        // Some ATS pages lock the input down; the popup falls back to FR-5.5.
        return false;
    }
}

/** Puts `value` in `field`. False means the field was understood but could not
 * be set — a listbox with no matching option, mostly — and stays a pending one. */
export async function fillField(field: ScannedField, value: string): Promise<boolean> {
    switch (field.kind) {
        case "text":
        case "textarea":
        case "date":
            return fillText(field.el, value);
        case "select":
            return field.el instanceof HTMLSelectElement ? fillSelect(field.el, value) : false;
        case "radio":
            return fillRadio(field.group, value);
        case "checkbox":
            return field.el instanceof HTMLInputElement ? fillCheckbox(field.el, value) : false;
        case "combobox":
            return fillCombobox(field.el, value);
        case "file":
            return false;
    }
}
