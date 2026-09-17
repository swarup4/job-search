import type {
    AccountRead,
    AnswerBankEntry,
    AtsPlatform,
    FieldFill,
    JobRead,
    ScreeningAnswer,
    ApplicationRead,
    UserProfile,
} from "@/shared/types";

/** Everything the content script needs, handed over in one message. It never
 * calls the worker back, so the token and the API stay on this side of the
 * boundary and the application page's world only ever sees answers. */
export interface FillData {
    profile: UserProfile;
    answerBank: AnswerBankEntry[];
    resume: { name: string; base64: string } | null;
}

/** A field found and understood, but with no answer to put in it. FR-5.2 stops
 * here rather than inventing one — the user answers it in the popup. */
export interface PendingQuestion {
    selector: string;
    question: string;
    kind: "text" | "textarea" | "select" | "radio" | "checkbox" | "date";
    options: string[];
}

export interface UserAnswer {
    selector: string;
    question: string;
    value: string;
}

export interface FrameResult {
    platform: AtsPlatform;
    filled: FieldFill[];
    pending: PendingQuestion[];
    /** Answers the user typed in the popup — `answeredByUser`, not derived. */
    answered: ScreeningAnswer[];
    resumeAttached: boolean;
    /** FR-5.5 — set when the resume could not be attached programmatically. */
    resumeHint: string | null;
    /** Why this frame could not be filled at all, when it could not. */
    blocked: string | null;
}

export interface TabContext {
    account: AccountRead | null;
    /** The staged application whose applyUrl matches the tab, when one does. */
    application: ApplicationRead | null;
    job: JobRead | null;
    /** Everything staged, so the popup can offer a manual pick. */
    staged: { application: ApplicationRead; job: JobRead | null }[];
    platform: AtsPlatform;
    fillable: boolean;
}

export type WorkerRequest =
    | { type: "context"; tabId: number }
    | { type: "signIn"; email: string; password: string }
    | { type: "signOut" }
    | { type: "fillTab"; tabId: number; applicationId: string }
    | { type: "answerTab"; tabId: number; applicationId: string; answers: UserAnswer[] }
    | { type: "clearHighlights"; tabId: number }
    | { type: "confirmSubmitted"; applicationId: string };

export type TabRequest =
    | { type: "ping" }
    | { type: "fill"; data: FillData }
    | { type: "answer"; answers: UserAnswer[] }
    | { type: "clear" };

export type Reply<T> = { ok: true; value: T } | { ok: false; error: string };

export async function askWorker<T>(request: WorkerRequest): Promise<T> {
    const reply = (await chrome.runtime.sendMessage(request)) as Reply<T> | undefined;
    if (!reply) throw new Error("The extension worker did not respond.");
    if (!reply.ok) throw new Error(reply.error);
    return reply.value;
}
