import { axiosInstance } from "@/lib/axiosInstance";

/** Both endpoints answer with the same shape, so both land here. */
function toSession(result) {
    return {
        token: result.access_token,
        user: {
            id: result.account.id,
            name: result.account.name,
            email: result.account.email,
            role: result.account.role,
        },
    };
}

/** POST /api/account/login. Shapes the session; storing it is the store's job. */
export async function login(credentials) {
    return toSession(await axiosInstance.post("/account/login", credentials));
}

/**
 * POST /api/account/signup. Signup returns a token of its own, so this does NOT
 * call login afterwards — one request, and you are signed in.
 */
export async function signup({ name, email, password }) {
    return toSession(await axiosInstance.post("/account/signup", { name, email, password }));
}

/** GET /api/account/getAccount/{id} — `role` lives on the account, not the profile. */
export function getAccount(accountId) {
    return axiosInstance.get(`/account/getAccount/${accountId}`);
}

/** PATCH /api/account/updateAccount/{id} — partial; sends only what changed. */
export function updateAccount(accountId, changes) {
    return axiosInstance.patch(`/account/updateAccount/${accountId}`, changes);
}
