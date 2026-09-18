import type {
    AccountRead,
    AnswerBankEntry,
    ApplicantProfile,
    AtsPlatform,
    CaptureRegion,
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
    applicant: ApplicantProfile;
    answerBank: AnswerBankEntry[];
    resume: { name: string; base64: string } | null;
    /** Whether the tab matches a staged application. The panel offers its submit
     * confirmation only when there is something to record it against. */
    tracked: boolean;
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
    /** Controls the scanner saw, answered or not. Zero means the form was not
     * found, which is a different failure from finding it and having no answers. */
    scanned: number;
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

/** What the popup shows after a capture. `duplicate` is the server saying this
 * exact page is already stored, which is a success and not an error. */
export interface CaptureOutcome {
    id: string;
    duplicate: boolean;
    pageTitle: string;
    region: CaptureRegion;
    characters: number;
    links: number;
}

export type WorkerRequest =
    | { type: "context"; tabId: number }
    | { type: "signIn"; email: string; password: string }
    | { type: "signOut" }
    | { type: "fillTab"; tabId: number; applicationId: string | null }
    | { type: "answerTab"; tabId: number; applicationId: string | null; answers: UserAnswer[] }
    | { type: "clearHighlights"; tabId: number }
    | { type: "showPanel"; tabId: number }
    | { type: "confirmSubmitted"; applicationId: string }
    | { type: "captureTab"; tabId: number }
    // Sent by the content script after the user answers in the in-page panel. It
    // carries no application id — the worker already knows which tab is which.
    | { type: "recordAnswers"; answered: ScreeningAnswer[] }
    // The same confirmation as `confirmSubmitted`, from the panel rather than the
    // popup, so it too names no application id.
    | { type: "confirmTabSubmitted" };

export type TabRequest =
    | { type: "ping" }
    | { type: "capture" }
    | { type: "panel" }
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
