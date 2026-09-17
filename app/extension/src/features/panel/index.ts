import { PANEL_CSS, PANEL_WIDTH } from "@/features/panel/style";
import { findBySelector } from "@/features/fieldFill/selector";
import type { FrameResult, PendingQuestion, UserAnswer } from "@/shared/messages";

/**
 * The review panel, docked into the application page itself rather than the
 * browser popup. A popup closes the moment you click the form, which is exactly
 * when you need it: the questions it could not answer are the ones you answer by
 * looking at the page.
 *
 * It lives in a shadow root for two reasons — the ATS cannot restyle it, and
 * `scan()` cannot see its inputs, because `querySelectorAll` does not cross a
 * shadow boundary. A panel whose own text boxes got filled would be a farce.
 */

const HOST_ID = "jobpilot-panel-host";

/**
 * Narrows the page instead of floating over it. The form is what the user reads
 * while they answer the questions, and an ATS puts its own submit bar and sticky
 * header at the edges — anything overlaid lands on top of one of them.
 */
function dock(): void {
    const { style } = document.documentElement;
    style.setProperty("width", `calc(100% - ${PANEL_WIDTH}px)`, "important");
    // Workday declares a min-width that would otherwise keep the page at full
    // width and put a horizontal scrollbar under the sidebar.
    style.setProperty("min-width", "0", "important");
}

function undock(): void {
    const { style } = document.documentElement;
    style.removeProperty("width");
    style.removeProperty("min-width");
}

export interface PanelHandlers {
    onAnswer: (answers: UserAnswer[]) => Promise<void>;
    onClearHighlights: () => void;
    /** Null when the tab matches nothing staged, so there is no application to move. */
    onSubmitted: (() => Promise<void>) | null;
}

function host(doc: Document): { element: HTMLElement; root: ShadowRoot } {
    const existing = doc.getElementById(HOST_ID);
    if (existing?.shadowRoot) return { element: existing, root: existing.shadowRoot };

    const element = doc.createElement("div");
    element.id = HOST_ID;
    const root = element.attachShadow({ mode: "open" });

    const style = doc.createElement("style");
    style.textContent = PANEL_CSS;
    root.append(style);

    // On `documentElement`, not `body`: an ATS that gives `body` a stacking
    // context of its own caps whatever z-index the panel asks for, and its
    // sticky submit bar then paints over the sidebar.
    doc.documentElement.append(element);
    return { element, root };
}

function tag(root: ShadowRoot, text: string, kind: string): HTMLElement {
    const span = root.ownerDocument.createElement("span");
    span.className = `tag ${kind}`;
    span.textContent = text;
    return span;
}

/** Takes the user to the field a question belongs to, and makes it obvious which. */
function reveal(selector: string): void {
    const el = findBySelector(selector);
    if (!el) return;

    el.scrollIntoView({ behavior: "smooth", block: "center" });
    const previous = el.style.boxShadow;
    el.style.boxShadow = "0 0 0 4px rgba(245, 158, 11, 0.55)";
    setTimeout(() => {
        el.style.boxShadow = previous;
    }, 1200);
}

function control(doc: Document, question: PendingQuestion): HTMLElement {
    if (question.kind === "select" && question.options.length > 0) {
        const select = doc.createElement("select");
        select.append(new Option("Leave blank", ""));
        for (const option of question.options) select.append(new Option(option, option));
        return select;
    }

    if (question.kind === "textarea") return doc.createElement("textarea");

    const input = doc.createElement("input");
    input.type = question.kind === "date" ? "text" : "text";
    return input;
}

export function renderPanel(result: FrameResult, handlers: PanelHandlers): void {
    const doc = document;
    const { root } = host(doc);
    dock();

    root.querySelector(".panel")?.remove();

    const panel = doc.createElement("aside");
    panel.className = "panel";

    // --- header
    const header = doc.createElement("header");
    const title = doc.createElement("div");
    title.className = "title";
    title.innerHTML = "JobPilot <span>· fills, never submits</span>";
    const close = doc.createElement("button");
    close.className = "icon";
    close.textContent = "×";
    close.title = "Close this panel (highlights stay)";
    close.addEventListener("click", () => closePanel());
    header.append(title, close);

    // --- body
    const body = doc.createElement("div");
    body.className = "body";

    const counts = doc.createElement("div");
    counts.className = "counts";
    counts.append(tag(root, `${result.filled.length} filled`, "good"));
    if (result.pending.length > 0) {
        counts.append(tag(root, `${result.pending.length} need you`, "warn"));
    }
    counts.append(
        tag(root, result.resumeAttached ? "resume attached" : "no resume", result.resumeAttached ? "good" : "plain"),
    );
    body.append(counts);

    if (result.resumeHint) body.append(hint(doc, result.resumeHint));

    if (result.filled.length === 0 && result.pending.length > 0) {
        body.append(
            hint(doc, "Nothing could be answered from what is stored. Fill these in — they go straight into the form."),
        );
    }

    const inputs = new Map<string, HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>();

    if (result.pending.length > 0) {
        const section = doc.createElement("section");
        const heading = doc.createElement("h2");
        heading.textContent = `Needs you (${result.pending.length})`;
        section.append(heading);

        const list = doc.createElement("ol");
        list.className = "questions";

        for (const question of result.pending) {
            const item = doc.createElement("li");

            const label = doc.createElement("label");
            label.textContent = question.question;
            label.title = "Show this field on the page";
            label.addEventListener("click", () => reveal(question.selector));

            const field = control(doc, question) as HTMLInputElement;
            field.addEventListener("focus", () => reveal(question.selector));
            inputs.set(question.selector, field);

            item.append(label, field);
            list.append(item);
        }

        const apply = doc.createElement("button");
        apply.className = "primary";
        apply.textContent = "Fill answers";
        apply.addEventListener("click", () => {
            const answers: UserAnswer[] = result.pending
                .map((question) => ({
                    selector: question.selector,
                    question: question.question,
                    value: inputs.get(question.selector)?.value.trim() ?? "",
                }))
                .filter((answer) => answer.value !== "");

            if (answers.length === 0) return;

            apply.disabled = true;
            apply.textContent = "Filling…";
            void handlers.onAnswer(answers).finally(() => {
                apply.disabled = false;
                apply.textContent = "Fill answers";
            });
        });

        section.append(list, apply);
        body.append(section);
    }

    if (result.filled.length > 0) {
        const details = doc.createElement("details");
        const summary = doc.createElement("summary");
        summary.textContent = `Filled (${result.filled.length})`;
        details.append(summary);

        const list = doc.createElement("ul");
        list.className = "fills";
        for (const field of result.filled) {
            const item = doc.createElement("li");
            const label = doc.createElement("span");
            label.className = "label";
            label.textContent = field.label;
            const value = doc.createElement("span");
            value.className = "value";
            value.textContent = field.value;
            item.append(label, value);
            list.append(item);
        }

        details.append(list);
        body.append(details);
    }

    // --- footer
    const note = doc.createElement("div");
    note.className = "note";
    note.textContent =
        "Review every highlighted field, then submit the form yourself. Nothing here can submit it.";

    const footer = doc.createElement("footer");
    const clear = doc.createElement("button");
    clear.textContent = "Clear highlights";
    clear.addEventListener("click", () => {
        handlers.onClearHighlights();
        closePanel();
    });
    footer.append(clear);

    const confirmSubmitted = handlers.onSubmitted;
    if (confirmSubmitted) {
        const submitted = doc.createElement("button");
        submitted.className = "confirm";
        submitted.textContent = "I submitted this";
        submitted.title = "Marks the application applied. Nothing else here can.";
        submitted.addEventListener("click", () => {
            submitted.disabled = true;
            submitted.textContent = "Recording…";
            void confirmSubmitted().then(
                () => {
                    submitted.textContent = "Marked as applied";
                },
                () => {
                    submitted.disabled = false;
                    submitted.textContent = "I submitted this";
                },
            );
        });
        footer.append(submitted);
    }

    panel.append(header, body, note, footer);
    root.append(panel);
}

function hint(doc: Document, text: string): HTMLElement {
    const paragraph = doc.createElement("p");
    paragraph.className = "hint";
    paragraph.textContent = text;
    return paragraph;
}

export function closePanel(): void {
    document.getElementById(HOST_ID)?.remove();
    undock();
}

export function panelIsOpen(): boolean {
    return document.getElementById(HOST_ID) !== null;
}
