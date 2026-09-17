/** FR-5.4 — an unmarked fill is a silent edit. Everything this extension touches
 * is outlined, and the banner says so, because the user submits the form. */

const STYLE_ID = "jobpilot-highlight-style";
export const FILLED_CLASS = "jobpilot-filled";
export const PENDING_CLASS = "jobpilot-pending";

const CSS_TEXT = `
.${FILLED_CLASS} {
    outline: 2px solid #22c55e !important;
    outline-offset: 1px !important;
    background-color: rgba(34, 197, 94, 0.07) !important;
    border-radius: 3px;
}
.${PENDING_CLASS} {
    outline: 2px dashed #f59e0b !important;
    outline-offset: 1px !important;
    background-color: rgba(245, 158, 11, 0.07) !important;
    border-radius: 3px;
}
`;

function ensureStyle(doc: Document): void {
    if (doc.getElementById(STYLE_ID)) return;
    const style = doc.createElement("style");
    style.id = STYLE_ID;
    style.textContent = CSS_TEXT;
    doc.head.append(style);
}

/** The control a user sees is not always the one that holds the value — a file
 * input hides behind a dropzone, a combobox behind a button. Outline whichever
 * of the two is actually on screen. */
function visibleAnchor(el: HTMLElement): HTMLElement {
    if (el.getBoundingClientRect().height > 0) return el;
    const parent = el.parentElement;
    return parent && parent.getBoundingClientRect().height > 0 ? parent : el;
}

export function markFilled(el: HTMLElement, note: string): void {
    ensureStyle(el.ownerDocument);
    const anchor = visibleAnchor(el);
    anchor.classList.add(FILLED_CLASS);
    anchor.setAttribute("title", `JobPilot filled this from ${note}`);
}

export function markPending(el: HTMLElement): void {
    ensureStyle(el.ownerDocument);
    const anchor = visibleAnchor(el);
    anchor.classList.add(PENDING_CLASS);
    anchor.setAttribute("title", "JobPilot has no answer for this one — you fill it in");
}

export function clearMarks(doc: Document): void {
    doc.querySelectorAll(`.${FILLED_CLASS}, .${PENDING_CLASS}`).forEach((el) => {
        el.classList.remove(FILLED_CLASS, PENDING_CLASS);
        el.removeAttribute("title");
    });
}
