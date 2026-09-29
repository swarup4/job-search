import { createSlice } from "@reduxjs/toolkit";

import { signedOut } from "@/store/auth/authSlice";

/**
 * `GET /api/status`, kept for every screen. Loaded when the shell mounts (so on every
 * page refresh), on the header's Refresh, and after an action that changes a number —
 * never per page, which is what made the numbers differ from one screen to the next.
 */
const initialState = {
    badges: { keywordSelections: 0, nextJobId: null, shortlisted: 0, staged: 0, pending: 0 },
    pipeline: { new: 0, shortlisted: 0, staged: 0, applied: 0, interview: 0 },
    jobs: { total: 0, unscored: 0, analyzed: 0 },
    discovery: { lastRunAt: null, companies: 0, ok: 0, failed: 0, blocked: 0, newJobs: 0 },
    profile: { indexedChunks: 0, pendingChunks: 0, lastIndexedAt: null, hasDefaultResume: false },
    serverTime: null,
    // When this tab last read it, for the header's "Synced …"; null before the first read,
    // which is also how a screen tells "not loaded yet" from a real zero.
    syncedAt: null,
};

const statusSlice = createSlice({
    name: "status",
    initialState,
    reducers: {
        statusLoaded(state, action) {
            const { badges, pipeline, jobs, discovery, profile, serverTime } = action.payload;
            Object.assign(state, { badges, pipeline, jobs, discovery, profile, serverTime });
            state.syncedAt = Date.now();
        },
    },
    // The next account to sign in on this tab must not see the last one's numbers.
    extraReducers: (builder) => builder.addCase(signedOut, () => initialState),
});

export const { statusLoaded } = statusSlice.actions;

export const selectStatus = (state) => state.status;

export default statusSlice.reducer;
