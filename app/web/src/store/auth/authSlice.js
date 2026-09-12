import { createSlice } from "@reduxjs/toolkit";

import { clearSession, readSession, writeSession } from "@/lib/session";

/**
 * Who is signed in. sessionStorage is the durable copy — it survives the refresh that
 * wipes the store — so the app reads it back once on mount and every page then takes
 * the user from here rather than touching storage itself.
 *
 * `status` starts "unknown" because sessionStorage does not exist while rendering on
 * the server. Only that first moment is undecided; after it, navigating is instant.
 */
const initialState = {
    status: "unknown", // unknown | authenticated | anonymous
    user: null,
};

const authSlice = createSlice({
    name: "auth",
    initialState,
    reducers: {
        /** Reads the stored session back into the store — once, when the app mounts. */
        sessionRestored(state) {
            const session = readSession();
            state.status = session?.token ? "authenticated" : "anonymous";
            state.user = session?.user ?? null;
        },
        signedIn(state, action) {
            writeSession(action.payload);
            state.status = "authenticated";
            state.user = action.payload.user;
        },
        signedOut(state) {
            clearSession();
            state.status = "anonymous";
            state.user = null;
        },
        /** After the profile page changes a field the account owns, such as `role`. */
        userChanged(state, action) {
            state.user = { ...state.user, ...action.payload };
            const session = readSession();
            if (session) writeSession({ ...session, user: state.user });
        },
    },
});

export const { sessionRestored, signedIn, signedOut, userChanged } = authSlice.actions;

export const selectUser = (state) => state.auth.user;
export const selectAuthStatus = (state) => state.auth.status;
export const selectIsAuthenticated = (state) => state.auth.status === "authenticated";

export default authSlice.reducer;
