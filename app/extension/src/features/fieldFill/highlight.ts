/** FR-5.4 — an unmarked fill is a silent edit. Everything this extension touches
 * is outlined, and the banner says so, because the user submits the form. */

const STYLE_ID = "jobpilot-highlight-style";
const BANNER_ID = "jobpilot-banner";
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
#${BANNER_ID} {
    position: fixed;
    right: 16px;
    bottom: 16px;
    z-index: 2147483647;
    max-width: 320px;
    padding: 12px 14px;
    border-radius: 10px;
    background: #0f172a;
    color: #e2e8f0;
    font: 13px/1.45 ui-sans-serif, system-ui, -apple-system, sans-serif;
    box-shadow: 0 10px 30px rgba(15, 23, 42, 0.35);
}
#${BANNER_ID} strong { color: #4ade80; font-weight: 600; }
#${BANNER_ID} em { color: #fbbf24; font-style: normal; font-weight: 600; }
#${BANNER_ID} button {
    margin-top: 8px;
    padding: 4px 8px;
    border: 1px solid #334155;
    border-radius: 6px;
    background: transparent;
    color: #94a3b8;
    font: inherit;
    cursor: pointer;
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

export function showBanner(doc: Document, filled: number, pending: number): void {
    ensureStyle(doc);
    doc.getElementById(BANNER_ID)?.remove();

    const banner = doc.createElement("div");
    banner.id = BANNER_ID;
    banner.innerHTML =
        `<div><strong>${filled} field${filled === 1 ? "" : "s"} filled</strong>` +
        (pending > 0 ? ` · <em>${pending} still need${pending === 1 ? "s" : ""} you</em>` : "") +
        `</div><div style="margin-top:4px;color:#94a3b8">Review every highlighted field. ` +
        `Nothing is submitted for you.</div>`;

    const dismiss = doc.createElement("button");
    dismiss.textContent = "Clear highlights";
    dismiss.addEventListener("click", () => clearMarks(doc));
    banner.append(dismiss);

    doc.body.append(banner);
}

export function clearMarks(doc: Document): void {
    doc.querySelectorAll(`.${FILLED_CLASS}, .${PENDING_CLASS}`).forEach((el) => {
        el.classList.remove(FILLED_CLASS, PENDING_CLASS);
        el.removeAttribute("title");
    });
    doc.getElementById(BANNER_ID)?.remove();
}
