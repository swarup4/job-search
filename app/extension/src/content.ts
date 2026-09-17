import { detect } from "@/features/ats";
import { attachFile, fillField } from "@/features/fieldFill/fill";
import { clearMarks, markFilled, markPending, showBanner } from "@/features/fieldFill/highlight";
import { resolve } from "@/features/fieldFill/match";
import { scan, type FieldKind, type ScannedField } from "@/features/fieldFill/scan";
import { findBySelector } from "@/features/fieldFill/selector";
import type {
    FillData,
    FrameResult,
    PendingQuestion,
    Reply,
    TabRequest,
    UserAnswer,
} from "@/shared/messages";
import type { FieldFill, ScreeningAnswer } from "@/shared/types";

/**
 * Runs in the application page's world, which is why it holds no token and makes
 * no network call: everything it needs arrives in the `fill` message and
 * everything it learns goes back in the reply. FR-5.3 — it has no submit path.
 */

function emptyResult(platform: FrameResult["platform"], blocked: string | null): FrameResult {
    return {
        platform,
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

async function runFill(data: FillData): Promise<FrameResult> {
    const adapter = detect();

    const blocked = adapter.blocked?.(document) ?? null;
    if (blocked) return emptyResult(adapter.platform, blocked);

    const root = adapter.root?.(document) ?? document;
    if (!root) return emptyResult(adapter.platform, null);

    const filled: FieldFill[] = [];
    const pending: PendingQuestion[] = [];

    for (const field of scan(root)) {
        if (field.kind === "file" || field.prefilled) continue;

        const resolution = resolve(field, data.profile, data.answerBank);
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

    if (filled.length > 0 || pending.length > 0) {
        showBanner(document, filled.length, pending.length);
    }

    return {
        platform: adapter.platform,
        filled,
        pending,
        answered: [],
        resumeAttached,
        resumeHint,
        blocked: null,
    };
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
async function runAnswers(answers: UserAnswer[]): Promise<FrameResult> {
    const adapter = detect();
    const answered: ScreeningAnswer[] = [];

    for (const answer of answers) {
        const el = findBySelector(answer.selector);
        if (!el) continue;

        const field = scan(el.parentElement ?? document).find(
            (candidate) => candidate.selector === answer.selector,
        );
        if (!field) continue;

        const ok = await fillField(field, answer.value);
        if (!ok) continue;

        el.classList.remove("jobpilot-pending");
        markFilled(el, "your own answer");
        answered.push({ question: answer.question, answer: answer.value, answeredByUser: true });
    }

    return { ...emptyResult(adapter.platform, null), answered };
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
    (request: TabRequest, _sender, respond: (reply: Reply<FrameResult | null>) => void) => {
        const run = async (): Promise<FrameResult | null> => {
            switch (request.type) {
                case "ping":
                    return null;
                case "fill":
                    return runFill(request.data);
                case "answer":
                    return runAnswers(request.answers);
                case "clear":
                    clearMarks(document);
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
