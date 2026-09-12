/**
 * The signed-in identity, in sessionStorage: it lasts for the tab and is gone when
 * the tab closes. Nothing reads it on the server, so every page behind AppShell
 * checks it on the client and the token rides on the Authorization header.
 *
 * Two tokens are stored. `token` is the short-lived one sent on every request;
 * `refreshToken` is sent only to /account/refresh, to replace `token` once it
 * expires, so a 60-minute TTL does not mean signing in every hour.
 */
const KEY = "jobpilot_session";

export function readSession() {
    if (typeof window === "undefined") return null;
    try {
        return JSON.parse(sessionStorage.getItem(KEY));
    } catch {
        // Private-mode browsers throw on access; a signed-out visitor, not a crash.
        return null;
    }
}

export function writeSession(session) {
    sessionStorage.setItem(KEY, JSON.stringify(session));
}

export function clearSession() {
    sessionStorage.removeItem(KEY);
}

export function readToken() {
    return readSession()?.token ?? null;
}

export function readRefreshToken() {
    return readSession()?.refreshToken ?? null;
}

/** After a refresh: the same user, a new pair of tokens. */
export function writeTokens({ token, refreshToken }) {
    const session = readSession();
    if (!session) return;
    writeSession({ ...session, token, refreshToken });
}
