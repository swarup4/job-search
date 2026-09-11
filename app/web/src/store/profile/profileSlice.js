import { createSlice, nanoid } from "@reduxjs/toolkit";

import profileData from "@/data/profile.json";

const initialState = {
    identity: {
        name: profileData.personal?.name ?? "",
        email: profileData.personal?.email ?? "",
        headline: profileData.personal?.headline ?? "",
        phone: profileData.personal?.phone ?? "",
        location: profileData.personal?.location ?? "",
        summary: profileData.summary ?? "",
        links: profileData.personal?.links ?? [],
    },
    experience: profileData.experience ?? [],
    education: profileData.education ?? [],
    certifications: profileData.certifications ?? [],
    skillGroups: profileData.skillGroups ?? [],
    // Unsaved edits are pending until the save bar persists them.
    dirty: false,
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

/** Marks save state rather than editing the profile, so it must not set `dirty`. */
const BOOKKEEPING = ["profile/profileSaved"];

const profileSlice = createSlice({
    name: "profile",
    initialState,
    reducers: {
        identityChanged(state, action) {
            const { field, value } = action.payload;
            state.identity[field] = value;
        },
        linkChanged(state, action) {
            const { index, value } = action.payload;
            const link = state.identity.links[index];
            if (link) link.value = value;
        },
        linkAdded(state, action) {
            state.identity.links.push({ label: action.payload, value: "" });
        },
        linkRemoved(state, action) {
            state.identity.links.splice(action.payload, 1);
        },

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

        skillGroupAdded(state, action) {
            state.skillGroups.push({ name: action.payload, items: [] });
        },
        skillAdded(state, action) {
            const { group, item } = action.payload;
            const g = state.skillGroups.find((s) => s.name === group);
            if (g && !g.items.includes(item)) g.items.push(item);
        },
        skillRemoved(state, action) {
            const { group, item } = action.payload;
            const g = state.skillGroups.find((s) => s.name === group);
            if (g) g.items = g.items.filter((i) => i !== item);
        },

        /** The API accepted the payload; what is in the store is now what is in the DB. */
        profileSaved(state) {
            state.dirty = false;
        },
    },
    extraReducers: (builder) => {
        // One place marks the profile dirty, so a new edit action cannot forget to.
        builder.addMatcher(
            (action) =>
                action.type.startsWith("profile/") && !BOOKKEEPING.includes(action.type),
            (state) => {
                state.dirty = true;
            }
        );
    },
});

export const {
    identityChanged,
    linkChanged,
    linkAdded,
    linkRemoved,
    roleAdded,
    roleUpdated,
    roleProjectsSet,
    educationAdded,
    educationUpdated,
    certificationAdded,
    certificationUpdated,
    skillGroupAdded,
    skillAdded,
    skillRemoved,
    profileSaved,
} = profileSlice.actions;

export const selectIdentity = (state) => state.profile.identity;
export const selectExperience = (state) => state.profile.experience;
export const selectEducation = (state) => state.profile.education;
export const selectCertifications = (state) => state.profile.certifications;
export const selectSkillGroups = (state) => state.profile.skillGroups;
export const selectSkillCount = (state) =>
    state.profile.skillGroups.reduce((n, g) => n + g.items.length, 0);
export const selectDirty = (state) => state.profile.dirty;

/**
 * The whole profile in the shape the API takes. Builds a fresh object, so read it
 * with store.getState() when saving rather than through useSelector.
 */
export function selectProfilePayload(state) {
    const { identity, experience, education, certifications, skillGroups } = state.profile;
    return {
        email: identity.email,
        personal: {
            name: identity.name,
            headline: identity.headline || null,
            phone: identity.phone || null,
            location: identity.location || null,
            links: identity.links,
        },
        summary: identity.summary || null,
        experience,
        education,
        certifications,
        skillGroups,
    };
}

export default profileSlice.reducer;
