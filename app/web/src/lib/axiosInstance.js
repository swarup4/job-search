import axios from "axios";

import { clearSession, readRefreshToken, readToken, writeTokens } from "@/lib/session";

/**
 * The one axios instance. Infrastructure, not domain — it knows how to reach the
 * API and what a failure looks like, and nothing about jobs, matches or resumes.
 * Every call in `src/services/` goes through it, so the base URL, timeout and
 * error shape are decided in exactly one place.
 *
 * NEXT_PUBLIC_ is required: client components call this from the browser. The
 * value is a localhost URL, not a secret — no key of any kind belongs here,
 * since anything NEXT_PUBLIC_ ships to the browser in the bundle.
 */
export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api";

/**
 * The AI tier's own server, for the few things the dashboard starts by hand (Run
 * discovery). It acts with the same token, so it gets the same interceptors.
 */
export const AI_URL = process.env.NEXT_PUBLIC_AI_URL ?? "http://127.0.0.1:8001/api";

export const axiosInstance = axios.create({
    baseURL: API_URL,
    timeout: 15000,
    headers: { "Content-Type": "application/json" },
});

export const aiInstance = axios.create({
    baseURL: AI_URL,
    timeout: 15000,
    headers: { "Content-Type": "application/json" },
});

/** What every failed call rejects with, whatever went wrong underneath. */
export class ApiError extends Error {
    constructor(message, { status = null, url = null, cause = null } = {}) {
        super(message);
        this.name = "ApiError";
        this.status = status;
        this.url = url;
        this.cause = cause;
    }

    get isOffline() {
        return this.status === null;
    }
}

/**
 * FastAPI puts the message in `detail` — a string for our domain errors, an array
 * of per-field objects for 422s. Both become one readable sentence, so callers
 * never dig through response.data themselves.
 */
function messageFrom(error) {
    const detail = error.response?.data?.detail;

    if (typeof detail === "string") return detail;

    if (Array.isArray(detail)) {
        return detail
            .map((item) => {
                const field = Array.isArray(item.loc) ? item.loc.slice(1).join(".") : null;
                return field ? `${field}: ${item.msg}` : item.msg;
            })
            .join("; ");
    }

    if (error.code === "ECONNABORTED") return "The API did not respond in time.";
    if (error.response) return `The API returned ${error.response.status}.`;

    return `Cannot reach the API at ${error.config?.baseURL ?? API_URL}. Is the server running?`;
}

// Renewed this long before it expires, so a request never leaves with a token that
// lapses on the way — which the server would answer with a 401 and a retry.
const EXPIRY_MARGIN_MS = 60_000;

function expiresSoon(token) {
    try {
        const payload = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
        const { exp } = JSON.parse(atob(payload));
        return typeof exp === "number" && exp * 1000 - Date.now() < EXPIRY_MARGIN_MS;
    } catch {
        // Unreadable: send it as it is, and the 401 retry below still covers it.
        return false;
    }
}

/** The access token, renewed first when it is about to expire. Shares the one
 * in-flight refresh, so a screen loading several calls at once refreshes once. */
export async function freshToken() {
    const token = readToken();
    if (token && expiresSoon(token)) return (await refreshAccessToken()) ?? token;
    return token;
}

async function attachToken(config) {
    const token = config.url?.endsWith(REFRESH_PATH) ? readToken() : await freshToken();
    if (token) config.headers.Authorization = `Bearer ${token}`;
    return config;
}

/**
 * A 401 the refresh could not rescue: the session is genuinely over. Dropping it
 * and sending the browser to the login page here means no caller has to handle
 * being signed out.
 */
function handleExpiry(status) {
    if (status !== 401 || typeof window === "undefined") return;
    if (window.location.pathname === "/login") return;

    clearSession();
    const next = encodeURIComponent(window.location.pathname + window.location.search);
    window.location.assign(`/login?next=${next}`);
}

const REFRESH_PATH = "/account/refresh";

/**
 * One refresh at a time, shared by everything waiting on it. Three calls failing
 * together on an expired token is the normal case — a screen usually loads several
 * at once — and without this they would each spend the refresh token, and the last
 * two would present one the server has already replaced.
 *
 * Resolves to the new access token, or null when the session cannot be saved.
 */
let refreshing = null;

function refreshAccessToken() {
    if (refreshing) return refreshing;

    refreshing = (async () => {
        const refreshToken = readRefreshToken();
        if (!refreshToken) return null;

        try {
            // Bare axios, not the instance: this call must not re-enter the
            // interceptor that is waiting on it.
            const { data } = await axios.post(`${API_URL}${REFRESH_PATH}`, {
                refreshToken: refreshToken,
            });
            writeTokens({ token: data.accessToken, refreshToken: data.refreshToken });
            return data.accessToken;
        } catch {
            // The refresh token is expired or rejected — sign in again.
            return null;
        }
    })().finally(() => {
        refreshing = null;
    });

    // Awaiters hold the promise itself, so clearing the variable above only means
    // the next expiry starts a fresh refresh.
    return refreshing;
}

/** Unwraps data on success; on a 401, refreshes once and replays on the same instance —
 * the backstop for a token that expired anyway (a laptop asleep past its expiry). */
function handleResponses(instance) {
    instance.interceptors.request.use(attachToken);
    instance.interceptors.response.use(
        (response) => response.data,
        async (error) => {
            const request = error.config;
            const canRetry =
                error.response?.status === 401 &&
                request &&
                !request._retried &&
                !request.url?.endsWith(REFRESH_PATH);

            if (canRetry) {
                request._retried = true;
                const token = await refreshAccessToken();
                if (token) {
                    request.headers.Authorization = `Bearer ${token}`;
                    return instance(request);
                }
            }

            handleExpiry(error.response?.status);

            // A `responseType: "blob"` request gets a Blob back even when the server
            // answered with a JSON error, so the detail has to be read out of it before
            // `messageFrom` can find it.
            if (error.response?.data instanceof Blob && error.response.data.type.includes("json")) {
                try {
                    error.response.data = JSON.parse(await error.response.data.text());
                } catch {
                    // Not JSON after all — messageFrom falls back to the status.
                }
            }

            const failure = new ApiError(messageFrom(error), {
                status: error.response?.status ?? null,
                url: error.config?.url ?? null,
                cause: error,
            });
            if (worthLogging(instance, error, failure)) {
                reportError({
                    message: failure.message,
                    context: {
                        method: error.config?.method?.toUpperCase() ?? null,
                        url: `${error.config?.baseURL ?? ""}${error.config?.url ?? ""}`,
                        status: failure.status,
                        page: window.location.pathname,
                    },
                });
            }
            return Promise.reject(failure);
        }
    );
}

handleResponses(axiosInstance);
handleResponses(aiInstance);

const ERROR_LOG_PATH = "/errorLog";

/**
 * 401 is the session ending and 404 is how `orNull` reads "not there yet" — neither is
 * a fault. The server's own 500s are skipped too: it logged them, with the traceback.
 */
function worthLogging(instance, error, failure) {
    if (typeof window === "undefined" || axios.isCancel(error)) return false;
    if (failure.status === 401 || failure.status === 404) return false;
    if (instance === axiosInstance && failure.status >= 500) return false;
    return !failure.url?.endsWith(ERROR_LOG_PATH);
}

/**
 * Adds a browser-side failure to the shared error log. Bare axios, so a failed report
 * cannot re-enter the interceptors, and it never throws: with the API down there is
 * nowhere to write it, and the error the user already sees has to stand alone.
 */
export function reportError({ message, detail = null, context = {} }) {
    const token = readToken();
    if (typeof window === "undefined" || !token) return;

    axios
        .post(
            `${API_URL}${ERROR_LOG_PATH}`,
            { message: String(message).slice(0, 2000), detail: detail?.slice(0, 20000) ?? null, context },
            { headers: { Authorization: `Bearer ${token}` } }
        )
        .catch(() => {});
}

/**
 * For reads whose absence is a normal state rather than a failure — no profile
 * yet, no match for a job. Only 404 is swallowed; every other error still throws.
 */
export async function orNull(promise) {
    try {
        return await promise;
    } catch (error) {
        if (error instanceof ApiError && error.status === 404) return null;
        throw error;
    }
}
