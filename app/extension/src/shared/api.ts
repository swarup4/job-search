import { API_URL } from "@/shared/config";
import { clearSession, readAccessToken, readPersisted, writeSession } from "@/shared/session";
import type {
    AnswerBankEntry,
    ApplicationRead,
    ApplicationStatus,
    FieldFill,
    JobRead,
    LoginResult,
    ScreeningAnswer,
    UserProfile,
} from "@/shared/types";

/**
 * The only place that talks to the API, and it runs in the service worker alone.
 * A content script sits in the application page's world; giving it the token, or
 * the fetch, would hand both to whatever else that page is running.
 */

export class ApiError extends Error {
    constructor(
        message: string,
        readonly status: number | null = null,
    ) {
        super(message);
        this.name = "ApiError";
    }
}

/** FastAPI puts a domain error in `detail` as a string, and a 422 as an array. */
function messageFrom(body: unknown, status: number): string {
    const detail = (body as { detail?: unknown } | null)?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
        return detail
            .map((item: { loc?: unknown[]; msg?: string }) => {
                const field = Array.isArray(item.loc) ? item.loc.slice(1).join(".") : null;
                return field ? `${field}: ${item.msg}` : (item.msg ?? "invalid");
            })
            .join("; ");
    }
    return `The API returned ${status}.`;
}

async function send(path: string, init: RequestInit, token: string | null): Promise<Response> {
    const headers = new Headers(init.headers);
    if (init.body) headers.set("Content-Type", "application/json");
    if (token) headers.set("Authorization", `Bearer ${token}`);

    try {
        return await fetch(`${API_URL}${path}`, { ...init, headers });
    } catch {
        throw new ApiError(`Cannot reach the API at ${API_URL}. Is the server running?`);
    }
}

/** A 401 means the 60-minute access token expired; swap it and retry once. */
async function refreshed(): Promise<string | null> {
    const persisted = await readPersisted();
    if (!persisted) return null;

    const response = await send(
        "/account/refresh",
        { method: "POST", body: JSON.stringify({ refreshToken: persisted.refreshToken }) },
        null,
    );
    if (!response.ok) {
        await clearSession();
        return null;
    }

    const result = (await response.json()) as LoginResult;
    await writeSession(result);
    return result.accessToken;
}

async function request<T>(path: string, init: RequestInit = {}, authed = true): Promise<T> {
    let token = authed ? await readAccessToken() : null;
    let response = await send(path, init, token);

    if (response.status === 401 && authed) {
        token = await refreshed();
        if (!token) throw new ApiError("Sign in again.", 401);
        response = await send(path, init, token);
    }

    if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new ApiError(messageFrom(body, response.status), response.status);
    }

    if (response.status === 204) return undefined as T;
    return (await response.json()) as T;
}

export async function login(email: string, password: string): Promise<LoginResult> {
    const result = await request<LoginResult>(
        "/account/login",
        { method: "POST", body: JSON.stringify({ email, password }) },
        false,
    );
    await writeSession(result);
    return result;
}

export function getProfile(): Promise<UserProfile> {
    return request<UserProfile>("/profile/getProfile");
}

export function getAnswerBank(): Promise<AnswerBankEntry[]> {
    return request<AnswerBankEntry[]>("/application/answer-bank");
}

export function listStaged(): Promise<ApplicationRead[]> {
    return request<ApplicationRead[]>("/application?status=staged");
}

export function getJob(jobId: string): Promise<JobRead> {
    return request<JobRead>(`/job/${jobId}`);
}

export function recordFill(
    applicationId: string,
    fieldsFilled: FieldFill[],
    screeningAnswers: ScreeningAnswer[],
): Promise<ApplicationRead> {
    return request<ApplicationRead>(`/application/fill/${applicationId}`, {
        method: "POST",
        body: JSON.stringify({ fieldsFilled, screeningAnswers }),
    });
}

export function setStatus(
    applicationId: string,
    status: ApplicationStatus,
    note: string | null,
    confirmedByUser: boolean,
): Promise<ApplicationRead> {
    return request<ApplicationRead>(`/application/status/${applicationId}`, {
        method: "PATCH",
        body: JSON.stringify({ status, note, confirmedByUser }),
    });
}

/**
 * The compiled base resume, base64 so it survives `chrome.runtime` messaging.
 * The content script cannot fetch this itself: its origin is the ATS page, which
 * the API's CORS list does not include.
 */
export async function getResumePdf(): Promise<{ name: string; base64: string }> {
    const token = await readAccessToken();
    const response = await send("/resume/base/pdf", {}, token);
    if (!response.ok) throw new ApiError("No base resume to attach yet.", response.status);

    const disposition = response.headers.get("Content-Disposition") ?? "";
    const name = /filename="([^"]+)"/.exec(disposition)?.[1] ?? "resume.pdf";
    const bytes = new Uint8Array(await response.arrayBuffer());

    let binary = "";
    for (const byte of bytes) binary += String.fromCharCode(byte);
    return { name, base64: btoa(binary) };
}
