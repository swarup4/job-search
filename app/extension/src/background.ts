import { matchApplication, platformFor } from "@/features/jobContext";
import * as api from "@/shared/api";
import type {
    CaptureOutcome,
    FillData,
    FrameResult,
    Reply,
    TabContext,
    TabRequest,
    UserAnswer,
    WorkerRequest,
} from "@/shared/messages";
import { clearSession, readAccount } from "@/shared/session";
import type { CapturePayload, FieldFill, JobRead, ScreeningAnswer } from "@/shared/types";

/**
 * The only context with the token and the only one that calls the API. It also
 * owns frame orchestration: a Greenhouse form is usually in an iframe, so a fill
 * has to reach every frame and add the answers up.
 */

const FILLABLE = new Set(["http:", "https:"]);

interface TabState {
    applicationId: string | null;
    filled: FieldFill[];
    answered: ScreeningAnswer[];
}

/** Session storage, not a module variable: the worker is evicted between clicks. */
async function readState(tabId: number): Promise<TabState | null> {
    const stored = await chrome.storage.session.get(`fill:${tabId}`);
    return (stored[`fill:${tabId}`] as TabState | undefined) ?? null;
}

async function writeState(tabId: number, state: TabState): Promise<void> {
    await chrome.storage.session.set({ [`fill:${tabId}`]: state });
}

async function tabUrl(tabId: number): Promise<string> {
    const tab = await chrome.tabs.get(tabId);
    return tab.url ?? "";
}

/** The declared content script covers the four known boards. Anywhere else it is
 * injected on demand, which `activeTab` permits because the user opened the popup. */
async function ensureInjected(tabId: number): Promise<void> {
    try {
        await chrome.tabs.sendMessage(tabId, { type: "ping" } satisfies TabRequest, { frameId: 0 });
        return;
    } catch {
        // Not there yet.
    }

    await chrome.scripting.executeScript({
        target: { tabId, allFrames: true },
        files: ["content.js"],
    });
}

/**
 * Three outcomes, and they are not the same thing. Most frames on a page have no
 * content script and that is normal. A frame whose script *ran and threw* is a
 * bug, and collapsing it into "no answer" is how a broken fill came back looking
 * like an empty page.
 */
type FrameOutcome =
    | { kind: "result"; value: FrameResult }
    | { kind: "error"; message: string }
    | { kind: "absent" };

async function sendToFrame(
    tabId: number,
    frameId: number,
    request: TabRequest,
): Promise<FrameOutcome> {
    let reply: Reply<FrameResult | null> | undefined;
    try {
        reply = (await chrome.tabs.sendMessage(tabId, request, { frameId })) as
            | Reply<FrameResult | null>
            | undefined;
    } catch {
        // No receiver in this frame, or it navigated away mid-fill.
        return { kind: "absent" };
    }

    if (!reply) return { kind: "absent" };
    if (!reply.ok) return { kind: "error", message: reply.error };
    return reply.value ? { kind: "result", value: reply.value } : { kind: "absent" };
}

async function broadcast(tabId: number, request: TabRequest): Promise<FrameOutcome[]> {
    await ensureInjected(tabId);

    const frames = (await chrome.webNavigation.getAllFrames({ tabId })) ?? [];
    return Promise.all(frames.map((frame) => sendToFrame(tabId, frame.frameId, request)));
}

/**
 * Adds the frames up, and — when nothing came back — says why. An empty review
 * with no explanation is the worst outcome here: the user cannot tell a page with
 * no form from a content script that never loaded, or from one that crashed.
 */
function merge(outcomes: FrameOutcome[]): FrameResult {
    const results = outcomes.flatMap((outcome) =>
        outcome.kind === "result" ? [outcome.value] : [],
    );
    const errors = outcomes.flatMap((outcome) =>
        outcome.kind === "error" ? [outcome.message] : [],
    );

    const filled = results.flatMap((result) => result.filled);
    const pending = results.flatMap((result) => result.pending);
    const answered = results.flatMap((result) => result.answered);
    const scanned = results.reduce((total, result) => total + result.scanned, 0);

    return {
        platform: results.find((result) => result.platform !== "other")?.platform ?? "other",
        scanned,
        filled,
        pending,
        answered,
        resumeAttached: results.some((result) => result.resumeAttached),
        resumeHint: results.find((result) => result.resumeHint)?.resumeHint ?? null,
        blocked: reasonNothingHappened(results, errors, filled.length + answered.length, scanned),
    };
}

function reasonNothingHappened(
    results: FrameResult[],
    errors: string[],
    touched: number,
    scanned: number,
): string | null {
    // An adapter knows best why its own page is not ready — a sign-in wall, an
    // unopened Easy Apply modal.
    const stated = results.find((result) => result.blocked)?.blocked;
    if (stated && touched === 0) return stated;

    // A crash inside the page beats every friendlier explanation: it is the truth.
    if (errors.length > 0 && touched === 0) return `The fill failed: ${errors[0]}`;

    if (touched > 0) return null;

    if (results.length === 0) {
        return "This page did not respond. Reload the tab and try again — the extension has to be loaded before the page is.";
    }

    if (scanned === 0) {
        return "No form fields found on this step. If this is a job description page, open the application form first.";
    }

    return null;
}

async function badge(tabId: number, count: number): Promise<void> {
    await chrome.action.setBadgeText({ tabId, text: count > 0 ? String(count) : "" });
    await chrome.action.setBadgeBackgroundColor({ tabId, color: "#16a34a" });
}

async function buildContext(tabId: number): Promise<TabContext> {
    const account = await readAccount();
    const url = await tabUrl(tabId);
    const platform = platformFor(url);
    const fillable = FILLABLE.has(new URL(url || "about:blank").protocol);

    if (!account) {
        return { account: null, application: null, job: null, staged: [], platform, fillable };
    }

    const applications = await api.listStaged();
    const jobs = new Map<string, JobRead | null>();

    await Promise.all(
        applications.map(async (application) => {
            jobs.set(application.jobId, await api.getJob(application.jobId).catch(() => null));
        }),
    );

    const application = matchApplication(url, applications);

    return {
        account,
        application,
        job: application ? (jobs.get(application.jobId) ?? null) : null,
        staged: applications.map((entry) => ({
            application: entry,
            job: jobs.get(entry.jobId) ?? null,
        })),
        platform,
        fillable,
    };
}

async function fillData(tracked: boolean): Promise<FillData> {
    const [profile, applicant, answerBank] = await Promise.all([
        api.getProfile(),
        api.getApplicant(),
        api.getAnswerBank(),
    ]);
    // No base resume, or LaTeX not installed, is a missing attachment — not a
    // reason to abandon the fill.
    const resume = await api.getResumePdf().catch(() => null);
    return { profile, applicant, answerBank, resume, tracked };
}

/** `applicationId` is null when the tab matches nothing staged. The fill still
 * runs — the profile is what answers the form — there is just no application to
 * record it against. */
async function fillTab(tabId: number, applicationId: string | null): Promise<FrameResult> {
    const data = await fillData(applicationId !== null);
    const result = merge(await broadcast(tabId, { type: "fill", data }));

    const answered = result.pending.map(
        (question): ScreeningAnswer => ({
            question: question.question,
            answer: null,
            answeredByUser: false,
        }),
    );

    await writeState(tabId, { applicationId, filled: result.filled, answered });
    if (applicationId) await api.recordFill(applicationId, result.filled, answered);
    await badge(tabId, result.filled.length);

    return result;
}

async function answerTab(
    tabId: number,
    applicationId: string | null,
    answers: UserAnswer[],
): Promise<FrameResult> {
    const result = merge(await broadcast(tabId, { type: "answer", answers }));

    const state = (await readState(tabId)) ?? { applicationId, filled: [], answered: [] };
    const byQuestion = new Map(state.answered.map((entry) => [entry.question, entry]));
    for (const entry of result.answered) byQuestion.set(entry.question, entry);

    const answered = [...byQuestion.values()];
    await writeState(tabId, { applicationId, filled: state.filled, answered });
    if (applicationId) await api.recordFill(applicationId, state.filled, answered);
    await badge(tabId, state.filled.length + result.answered.length);

    return result;
}

/**
 * Frame 0 only, and deliberately not `broadcast`: a capture is one page, and
 * merging frames is a fill-shaped operation returning a fill-shaped result.
 */
async function captureTab(tabId: number): Promise<CaptureOutcome> {
    await ensureInjected(tabId);

    let reply: Reply<CapturePayload | null> | undefined;
    try {
        reply = (await chrome.tabs.sendMessage(tabId, { type: "capture" } satisfies TabRequest, {
            frameId: 0,
        })) as Reply<CapturePayload | null> | undefined;
    } catch {
        throw new Error("This page did not respond. Reload the tab and try again.");
    }

    if (!reply) throw new Error("This page did not respond. Reload the tab and try again.");
    if (!reply.ok) throw new Error(reply.error);
    if (!reply.value) throw new Error("Found nothing to capture on this page.");

    const page = reply.value;
    const created = await api.createCapture(page);

    return {
        ...created,
        pageTitle: page.pageTitle,
        region: page.region,
        characters: page.markdown.length,
        links: page.links.length,
    };
}

const handlers: {
    [K in WorkerRequest["type"]]: (
        request: Extract<WorkerRequest, { type: K }>,
        sender: chrome.runtime.MessageSender,
    ) => Promise<unknown>;
} = {
    context: (request) => buildContext(request.tabId),

    signIn: async (request) => {
        const result = await api.login(request.email, request.password);
        return result.account;
    },

    signOut: async () => {
        await clearSession();
        return null;
    },

    fillTab: (request) => fillTab(request.tabId, request.applicationId),

    captureTab: (request) => captureTab(request.tabId),

    answerTab: (request) => answerTab(request.tabId, request.applicationId, request.answers),

    showPanel: async (request) => {
        await broadcast(request.tabId, { type: "panel" });
        return null;
    },

    clearHighlights: async (request) => {
        await broadcast(request.tabId, { type: "clear" });
        await badge(request.tabId, 0);
        return null;
    },

    // NFR-7 — `confirmedByUser` is the user saying they pressed Submit. Nothing
    // in this extension can reach APPLIED without it.
    confirmSubmitted: async (request) =>
        api.setStatus(request.applicationId, "applied", "Submitted from the extension", true),

    confirmTabSubmitted: async (_request, sender) => {
        const tabId = sender.tab?.id;
        if (tabId === undefined) return null;

        const state = await readState(tabId);
        if (!state?.applicationId) return null;

        return api.setStatus(
            state.applicationId,
            "applied",
            "Submitted from the extension",
            true,
        );
    },

    recordAnswers: async (request, sender) => {
        const tabId = sender.tab?.id;
        if (tabId === undefined) return null;

        const state = await readState(tabId);
        // Nothing staged matched this tab, so the fill was never recorded and
        // these answers have no application to belong to either.
        if (!state?.applicationId) return null;

        const byQuestion = new Map(state.answered.map((entry) => [entry.question, entry]));
        for (const entry of request.answered) byQuestion.set(entry.question, entry);
        const answered = [...byQuestion.values()];

        await writeState(tabId, { ...state, answered });
        await api.recordFill(state.applicationId, state.filled, answered);
        return null;
    },
};

chrome.runtime.onMessage.addListener(
    (request: WorkerRequest, sender, respond: (reply: Reply<unknown>) => void) => {
        const handler = handlers[request.type] as (
            req: WorkerRequest,
            from: chrome.runtime.MessageSender,
        ) => Promise<unknown>;
        if (!handler) {
            respond({ ok: false, error: `Unknown request: ${request.type}` });
            return false;
        }

        handler(request, sender)
            .then((value) => respond({ ok: true, value }))
            .catch((error: unknown) => {
                respond({ ok: false, error: error instanceof Error ? error.message : String(error) });
            });

        return true;
    },
);

chrome.tabs.onRemoved.addListener((tabId) => {
    void chrome.storage.session.remove(`fill:${tabId}`);
});
