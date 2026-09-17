import { matchApplication, platformFor } from "@/features/jobContext";
import * as api from "@/shared/api";
import type {
    FillData,
    FrameResult,
    Reply,
    TabContext,
    TabRequest,
    UserAnswer,
    WorkerRequest,
} from "@/shared/messages";
import { clearSession, readAccount } from "@/shared/session";
import type { ApplicationRead, FieldFill, JobRead, ScreeningAnswer } from "@/shared/types";

/**
 * The only context with the token and the only one that calls the API. It also
 * owns frame orchestration: a Greenhouse form is usually in an iframe, so a fill
 * has to reach every frame and add the answers up.
 */

const FILLABLE = new Set(["http:", "https:"]);

interface TabState {
    applicationId: string;
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

async function sendToFrame(
    tabId: number,
    frameId: number,
    request: TabRequest,
): Promise<FrameResult | null> {
    try {
        const reply = (await chrome.tabs.sendMessage(tabId, request, { frameId })) as
            | Reply<FrameResult | null>
            | undefined;
        return reply?.ok ? reply.value : null;
    } catch {
        // A frame with no content script, or one that navigated away mid-fill.
        return null;
    }
}

async function broadcast(tabId: number, request: TabRequest): Promise<FrameResult[]> {
    await ensureInjected(tabId);

    const frames = (await chrome.webNavigation.getAllFrames({ tabId })) ?? [];
    const results = await Promise.all(
        frames.map((frame) => sendToFrame(tabId, frame.frameId, request)),
    );

    return results.filter((result): result is FrameResult => result !== null);
}

function merge(results: FrameResult[]): FrameResult {
    const filled = results.flatMap((result) => result.filled);
    const pending = results.flatMap((result) => result.pending);
    const answered = results.flatMap((result) => result.answered);

    // A frame's "blocked" only matters when no frame managed anything.
    const blocked =
        filled.length === 0 && answered.length === 0
            ? (results.find((result) => result.blocked)?.blocked ?? null)
            : null;

    return {
        platform: results.find((result) => result.platform !== "other")?.platform ?? "other",
        filled,
        pending,
        answered,
        resumeAttached: results.some((result) => result.resumeAttached),
        resumeHint: results.find((result) => result.resumeHint)?.resumeHint ?? null,
        blocked,
    };
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

async function fillData(): Promise<FillData> {
    const [profile, answerBank] = await Promise.all([api.getProfile(), api.getAnswerBank()]);
    // No base resume, or LaTeX not installed, is a missing attachment — not a
    // reason to abandon the fill.
    const resume = await api.getResumePdf().catch(() => null);
    return { profile, answerBank, resume };
}

async function fillTab(tabId: number, applicationId: string): Promise<FrameResult> {
    const data = await fillData();
    const result = merge(await broadcast(tabId, { type: "fill", data }));

    const answered = result.pending.map(
        (question): ScreeningAnswer => ({
            question: question.question,
            answer: null,
            answeredByUser: false,
        }),
    );

    await writeState(tabId, { applicationId, filled: result.filled, answered });
    await api.recordFill(applicationId, result.filled, answered);
    await badge(tabId, result.filled.length);

    return result;
}

async function answerTab(
    tabId: number,
    applicationId: string,
    answers: UserAnswer[],
): Promise<FrameResult> {
    const result = merge(await broadcast(tabId, { type: "answer", answers }));

    const state = (await readState(tabId)) ?? { applicationId, filled: [], answered: [] };
    const byQuestion = new Map(state.answered.map((entry) => [entry.question, entry]));
    for (const entry of result.answered) byQuestion.set(entry.question, entry);

    const answered = [...byQuestion.values()];
    await writeState(tabId, { applicationId, filled: state.filled, answered });
    await api.recordFill(applicationId, state.filled, answered);
    await badge(tabId, state.filled.length + result.answered.length);

    return result;
}

const handlers: {
    [K in WorkerRequest["type"]]: (
        request: Extract<WorkerRequest, { type: K }>,
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

    answerTab: (request) => answerTab(request.tabId, request.applicationId, request.answers),

    clearHighlights: async (request) => {
        await broadcast(request.tabId, { type: "clear" });
        await badge(request.tabId, 0);
        return null;
    },

    // NFR-7 — `confirmedByUser` is the user saying they pressed Submit. Nothing
    // in this extension can reach APPLIED without it.
    confirmSubmitted: async (request) =>
        api.setStatus(request.applicationId, "applied", "Submitted from the extension", true),
};

chrome.runtime.onMessage.addListener(
    (request: WorkerRequest, _sender, respond: (reply: Reply<unknown>) => void) => {
        const handler = handlers[request.type] as (req: WorkerRequest) => Promise<unknown>;
        if (!handler) {
            respond({ ok: false, error: `Unknown request: ${request.type}` });
            return false;
        }

        handler(request)
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
