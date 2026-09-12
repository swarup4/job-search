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

export const axiosInstance = axios.create({
    baseURL: API_URL,
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

    return `Cannot reach the API at ${API_URL}. Is the server running?`;
}

axiosInstance.interceptors.request.use((config) => {
    const token = readToken();
    if (token) config.headers.Authorization = `Bearer ${token}`;
    return config;
});

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
                refresh_token: refreshToken,
            });
            writeTokens({ token: data.access_token, refreshToken: data.refresh_token });
            return data.access_token;
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

axiosInstance.interceptors.response.use(
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
                return axiosInstance(request);
            }
        }

        handleExpiry(error.response?.status);
        return Promise.reject(
            new ApiError(messageFrom(error), {
                status: error.response?.status ?? null,
                url: error.config?.url ?? null,
                cause: error,
            })
        );
    }
);

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
