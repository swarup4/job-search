import { detect } from "@/features/ats";
import { capturePage } from "@/features/capture";
import { attachFile, fillField } from "@/features/fieldFill/fill";
import { clearMarks, markFilled, markPending, PENDING_CLASS } from "@/features/fieldFill/highlight";
import { resolve } from "@/features/fieldFill/match";
import { scan, type FieldKind, type ScannedField } from "@/features/fieldFill/scan";
import { closePanel, renderPanel } from "@/features/panel";
import {
    askWorker,
    type FillData,
    type FrameResult,
    type PendingQuestion,
    type Reply,
    type TabRequest,
    type UserAnswer,
} from "@/shared/messages";
import type { CapturePayload, FieldFill, ScreeningAnswer } from "@/shared/types";

/** The last fill, so the panel can be redrawn after the user answers part of it.
 * Module state is safe here — a content script lives as long as its page. */
let lastResult: FrameResult | null = null;

/** Whether this tab's fill was recorded against a staged application. Only then
 * is there anything for the panel's submit confirmation to move. */
let tracked = false;

/**
 * Runs in the application page's world, which is why it holds no token and makes
 * no network call: everything it needs arrives in the `fill` message and
 * everything it learns goes back in the reply. FR-5.3 — it has no submit path.
 */

function emptyResult(platform: FrameResult["platform"], blocked: string | null): FrameResult {
    return {
        platform,
        scanned: 0,
        filled: [],
        pending: [],
        answered: [],
        resumeAttached: false,
        resumeHint: null,
        blocked,
    };
}

/** The popup renders a control per pending question, so a combobox has to come
 * back as something it can draw. */
function pendingKind(kind: FieldKind): PendingQuestion["kind"] | null {
    if (kind === "file") return null;
    if (kind === "combobox") return "select";
    return kind;
}

function asPending(field: ScannedField): PendingQuestion | null {
    const kind = pendingKind(field.kind);
    if (!kind) return null;
    markPending(field.el);
    return { selector: field.selector, question: field.label, kind, options: field.options };
}

export async function runFill(data: FillData): Promise<FrameResult> {
    tracked = data.tracked;
    const adapter = detect();

    const blocked = adapter.blocked?.(document) ?? null;
    if (blocked) return emptyResult(adapter.platform, blocked);

    const root = adapter.root?.(document) ?? document;
    if (!root) return emptyResult(adapter.platform, null);

    const filled: FieldFill[] = [];
    const pending: PendingQuestion[] = [];
    const fields = scan(root);

    for (const field of fields) {
        if (field.kind === "file" || field.prefilled) continue;

        const resolution = resolve(field, data.profile, data.applicant, data.answerBank);
        if (!resolution) {
            const question = asPending(field);
            if (question) pending.push(question);
            continue;
        }

        const override = await adapter.fill?.(field, resolution.value);
        const ok = override ?? (await fillField(field, resolution.value));

        if (!ok) {
            const question = asPending(field);
            if (question) pending.push(question);
            continue;
        }

        markFilled(field.el, resolution.source === "profile" ? "your profile" : "your answer bank");
        filled.push({
            selector: field.selector,
            label: field.label,
            value: resolution.value,
            source: resolution.source,
            highlighted: true,
        });
    }

    const { resumeAttached, resumeHint } = attachResume(adapter, data);

    const outcome: FrameResult = {
        platform: adapter.platform,
        scanned: fields.length,
        filled,
        pending,
        answered: [],
        resumeAttached,
        resumeHint,
        blocked: null,
    };

    if (filled.length > 0 || pending.length > 0) show(outcome);
    return outcome;
}

/**
 * Draws the review panel into the page. The popup cannot do this job: it closes
 * the moment the user clicks the form, which is precisely when they are working
 * through the questions it could not answer.
 */
function show(result: FrameResult): void {
    lastResult = result;
    renderPanel(result, {
        onAnswer: applyAnswers,
        onClearHighlights: () => clearMarks(document),
        // NFR-7 — the user saying they pressed Submit, from the page where they
        // pressed it. The worker holds the application id, as it does for answers.
        onSubmitted: tracked
            ? async () => {
                  await askWorker({ type: "confirmTabSubmitted" });
              }
            : null,
    });
}

/** Fills what the user typed in the panel, drops those questions from it, and
 * tells the worker so the answers reach the application record. */
async function applyAnswers(answers: UserAnswer[]): Promise<void> {
    const outcome = await runAnswers(answers);
    if (outcome.answered.length === 0) return;

    const done = new Set(outcome.answered.map((entry) => entry.question));
    const merged: FrameResult = {
        ...(lastResult ?? outcome),
        filled: [...(lastResult?.filled ?? []), ...outcome.filled],
        pending: (lastResult?.pending ?? []).filter((question) => !done.has(question.question)),
    };

    show(merged);

    // Outbound only — the worker holds the token and the application id, and this
    // side never learns either.
    await chrome.runtime.sendMessage({ type: "recordAnswers", answered: outcome.answered });
}

function attachResume(
    adapter: ReturnType<typeof detect>,
    data: FillData,
): { resumeAttached: boolean; resumeHint: string | null } {
    const input = adapter.resumeInput?.(document) ?? null;
    if (!input) return { resumeAttached: false, resumeHint: null };

    if (!data.resume) {
        return { resumeAttached: false, resumeHint: "No base resume saved yet — attach one by hand." };
    }

    const ok = attachFile(input, data.resume.name, data.resume.base64);
    if (ok) {
        markFilled(input, "your base resume");
        return { resumeAttached: true, resumeHint: null };
    }

    markPending(input);
    return {
        resumeAttached: false,
        resumeHint: `This page blocks programmatic uploads — attach ${data.resume.name} yourself.`,
    };
}

/** The user answered a pending question in the popup. Their answer is recorded as
 * `answeredByUser`, never as something the extension worked out. */
export async function runAnswers(answers: UserAnswer[]): Promise<FrameResult> {
    const adapter = detect();
    const root = adapter.root?.(document) ?? document;

    // Scanned once, over the same root the fill used, and indexed by selector.
    // Rescanning around each element narrowed the scope enough that a control
    // sharing its wrapper with another lost its label and was silently dropped.
    const fields = new Map(scan(root).map((field) => [field.selector, field]));

    const answered: ScreeningAnswer[] = [];
    const filled: FieldFill[] = [];

    for (const answer of answers) {
        const field = fields.get(answer.selector);
        if (!field) continue;

        const override = await adapter.fill?.(field, answer.value);
        const ok = override ?? (await fillField(field, answer.value));
        if (!ok) continue;

        field.el.classList.remove(PENDING_CLASS);
        markFilled(field.el, "your own answer");
        answered.push({ question: answer.question, answer: answer.value, answeredByUser: true });
        filled.push({
            selector: field.selector,
            label: field.label,
            value: answer.value,
            source: "answer_bank",
            highlighted: true,
        });
    }

    return { ...emptyResult(adapter.platform, null), filled, answered };
}

declare global {
    interface Window {
        __jobpilotLoaded?: true;
    }
}

/**
 * Guards against a second copy in the same frame. Greenhouse embeds its form in
 * an iframe below an unmatched top frame, so the worker's `ping` to frame 0 fails
 * and it injects into every frame — including the one the declared content script
 * already runs in. Two listeners there would fill the form twice.
 */
function register(): void {
    chrome.runtime.onMessage.addListener(
    (
        request: TabRequest,
        _sender,
        respond: (reply: Reply<FrameResult | CapturePayload | null>) => void,
    ) => {
        const run = async (): Promise<FrameResult | CapturePayload | null> => {
            switch (request.type) {
                case "ping":
                    return null;
                case "capture":
                    return capturePage();
                case "panel":
                    if (lastResult) show(lastResult);
                    return null;
                case "fill":
                    return runFill(request.data);
                case "answer":
                    return runAnswers(request.answers);
                case "clear":
                    clearMarks(document);
                    closePanel();
                    lastResult = null;
                    return null;
            }
        };

        run()
            .then((value) => respond({ ok: true, value }))
            .catch((error: unknown) => {
                respond({ ok: false, error: error instanceof Error ? error.message : String(error) });
            });

        // Keeps the channel open for the async work above.
        return true;
    },
    );
}

if (!window.__jobpilotLoaded) {
    window.__jobpilotLoaded = true;
    register();
}
