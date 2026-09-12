/**
 * The signed-in identity, in sessionStorage: it lasts for the tab and is gone when
 * the tab closes. Nothing reads it on the server, so every page behind AppShell
 * checks it on the client and the token rides on the Authorization header.
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
