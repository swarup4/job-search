import { axiosInstance } from "@/lib/axiosInstance";
import { writeSession } from "@/lib/session";

/**
 * POST /api/account/login. Returns the signed-in user and, as a side effect, stores
 * the session — every caller needs that to have happened, so none of them has to
 * remember to do it.
 */
export async function login(credentials) {
    const result = await axiosInstance.post("/account/login", credentials);
    const session = {
        token: result.access_token,
        user: {
            id: result.account.id,
            name: result.account.name,
            email: result.account.email,
        },
    };
    writeSession(session);
    return session;
}

/** POST /api/account/signup, then straight in — a new account is signed in already. */
export async function signup({ name, email, password }) {
    await axiosInstance.post("/account/signup", { name, email, password });
    return login({ email, password });
}
