import axios from "axios";

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

axiosInstance.interceptors.response.use(
    (response) => response.data,
    (error) =>
        Promise.reject(
            new ApiError(messageFrom(error), {
                status: error.response?.status ?? null,
                url: error.config?.url ?? null,
                cause: error,
            })
        )
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
