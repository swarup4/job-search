import type { AccountRead, LoginResult } from "@/shared/types";

/**
 * The access token lives in `storage.session` — memory-backed, wiped when Chrome
 * restarts, and unreadable from a content script, so a hostile application page
 * cannot reach it. The refresh token and account go to `storage.local` so a
 * browser restart does not mean signing in again.
 */
const ACCESS_KEY = "accessToken";
const PERSISTED_KEY = "session";

interface Persisted {
    refreshToken: string;
    account: AccountRead;
}

export async function readAccessToken(): Promise<string | null> {
    const stored = await chrome.storage.session.get(ACCESS_KEY);
    return (stored[ACCESS_KEY] as string | undefined) ?? null;
}

export async function readPersisted(): Promise<Persisted | null> {
    const stored = await chrome.storage.local.get(PERSISTED_KEY);
    return (stored[PERSISTED_KEY] as Persisted | undefined) ?? null;
}

export async function writeSession(result: LoginResult): Promise<void> {
    await chrome.storage.session.set({ [ACCESS_KEY]: result.accessToken });
    await chrome.storage.local.set({
        [PERSISTED_KEY]: { refreshToken: result.refreshToken, account: result.account },
    });
}

export async function clearSession(): Promise<void> {
    await chrome.storage.session.remove(ACCESS_KEY);
    await chrome.storage.local.remove(PERSISTED_KEY);
}

export async function readAccount(): Promise<AccountRead | null> {
    return (await readPersisted())?.account ?? null;
}
