import { createSlice } from "@reduxjs/toolkit";

import { signedOut } from "@/store/auth/authSlice";

/**
 * The badges the header and sidebar show on every screen. Loaded once when the shell
 * mounts and refreshed after an action that changes them — never per page, which is
 * what made the numbers differ from one screen to the next.
 */
const initialState = {
    pending: 0,
    shortlisted: 0,
    // When the counts were last read, for the header's "Synced …"; null before the first.
    syncedAt: null,
};

const shellSlice = createSlice({
    name: "shell",
    initialState,
    reducers: {
        shellCountsLoaded(state, action) {
            state.pending = action.payload.pending;
            state.shortlisted = action.payload.shortlisted;
            state.syncedAt = Date.now();
        },
    },
    // The next account to sign in on this tab must not see the last one's numbers.
    extraReducers: (builder) => builder.addCase(signedOut, () => initialState),
});

export const { shellCountsLoaded } = shellSlice.actions;

export const selectShell = (state) => state.shell;

export default shellSlice.reducer;
