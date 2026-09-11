import { createSlice, nanoid } from "@reduxjs/toolkit";

import profileData from "@/data/profile.json";

const initialState = {
    experience: profileData.experience ?? [],
    education: profileData.education ?? [],
    certifications: profileData.certifications ?? [],
};

// Ids come from `prepare`: a reducer calling nanoid() replays differently under
// DevTools time-travel.
function appendTo(list, prefix) {
    return {
        reducer(state, action) {
            state[list].push(action.payload);
        },
        prepare(entry) {
            return { payload: { ...entry, id: `${prefix}-${nanoid(8)}` } };
        },
    };
}

function patchIn(list) {
    return (state, action) => {
        const { id, changes } = action.payload;
        const entry = state[list].find((e) => e.id === id);
        if (entry) Object.assign(entry, changes);
    };
}

const profileSlice = createSlice({
    name: "profile",
    initialState,
    reducers: {
        roleAdded: appendTo("experience", "exp"),
        roleUpdated: patchIn("experience"),
        roleProjectsSet(state, action) {
            const { id, projects } = action.payload;
            const role = state.experience.find((r) => r.id === id);
            if (role) role.projects = projects;
        },

        educationAdded: appendTo("education", "edu"),
        educationUpdated: patchIn("education"),

        certificationAdded: appendTo("certifications", "cert"),
        certificationUpdated: patchIn("certifications"),
    },
});

export const {
    roleAdded,
    roleUpdated,
    roleProjectsSet,
    educationAdded,
    educationUpdated,
    certificationAdded,
    certificationUpdated,
} = profileSlice.actions;

export const selectExperience = (state) => state.profile.experience;
export const selectEducation = (state) => state.profile.education;
export const selectCertifications = (state) => state.profile.certifications;

export default profileSlice.reducer;
