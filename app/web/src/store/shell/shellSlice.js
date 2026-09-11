import { createSlice } from "@reduxjs/toolkit";

const initialState = { pending: 0, shortlisted: 0 };

const shellSlice = createSlice({
    name: "shell",
    initialState,
    reducers: {
        countsSet(state, action) {
            const { pending = 0, shortlisted = 0 } = action.payload ?? {};
            state.pending = pending;
            state.shortlisted = shortlisted;
        },
    },
});

export const { countsSet } = shellSlice.actions;

export const selectCounts = (state) => state.shell;

export default shellSlice.reducer;
