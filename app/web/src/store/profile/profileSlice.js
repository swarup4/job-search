import { createSlice } from "@reduxjs/toolkit";

/**
 * Starts empty. Nothing here is seeded from a fixture any more — `getProfile()`
 * fills it from the API on mount, which can only happen on the client because the
 * bearer token lives in sessionStorage.
 */
const initialState = {
    // idle | loading | ready | error
    status: "idle",
    error: null,
    // False until the profile row exists on the server; the first save creates it.
    exists: false,
    identity: {
        name: "",
        email: "",
        headline: "",
        role: "",
        phone: "",
        location: "",
        summary: "",
        links: [],
    },
    experience: [],
    education: [],
    certifications: [],
    skillGroups: [],
    // The identity as last persisted. Edits are diffed against it, so a save calls
    // only the endpoint whose data actually changed.
    saved: null,
};

/** The server sends null for an empty optional; the inputs want a string. */
const text = (value) => value ?? "";

/** The account row owns these two; the profile row owns the rest of the identity. */
const ACCOUNT_FIELDS = ["name", "role"];
const PROFILE_FIELDS = ["headline", "phone", "location", "summary", "links"];

const snapshot = (identity) => ({ ...identity, links: identity.links.map((l) => ({ ...l })) });
const equal = (a, b) => JSON.stringify(a) === JSON.stringify(b);

// Entries arrive already saved, so the payload is whatever the server stored — its
// id included. Nothing here invents one.
function appendTo(list) {
    return (state, action) => {
        state[list].push(action.payload);
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
        /** Puts the load back to square one, so the mount effect fetches again. */
        profileReload(state) {
            state.status = "idle";
            state.error = null;
        },

        profileLoading(state) {
            state.status = "loading";
            state.error = null;
        },

        /**
         * Replaces everything with the one aggregated response. Name, email and role
         * sit at the top of it — those three columns live on `accounts`, not
         * `profile` — and `profile` is null until personal details are saved.
         */
        profileLoaded(state, action) {
            const { name, email, role, profile, work, education, skill, certification } =
                action.payload;

            state.status = "ready";
            state.error = null;
            state.exists = Boolean(profile);
            state.identity = {
                name: text(name),
                email: text(email),
                role: text(role),
                headline: text(profile?.headline),
                phone: text(profile?.phone),
                location: text(profile?.location),
                summary: text(profile?.summary),
                links: profile?.links ?? [],
            };
            state.experience = work ?? [];
            state.education = education ?? [];
            state.skillGroups = skill ?? [];
            state.certifications = certification ?? [];
            state.saved = snapshot(state.identity);
        },

        profileFailed(state, action) {
            state.status = "error";
            state.error = action.payload;
        },

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

        roleAdded: appendTo("experience"),
        roleUpdated: patchIn("experience"),

        educationAdded: appendTo("education"),
        educationUpdated: patchIn("education"),

        certificationAdded: appendTo("certifications"),
        certificationUpdated: patchIn("certifications"),

        skillGroupAdded: appendTo("skillGroups"),
        skillGroupUpdated: patchIn("skillGroups"),

        /** Personal details are saved; the row now exists whether or not it did. */
        profileSaved(state) {
            state.exists = true;
            state.saved = snapshot(state.identity);
        },
    },
});

export const {
    profileReload,
    profileLoading,
    profileLoaded,
    profileFailed,
    identityChanged,
    linkChanged,
    linkAdded,
    linkRemoved,
    roleAdded,
    roleUpdated,
    educationAdded,
    educationUpdated,
    certificationAdded,
    certificationUpdated,
    skillGroupAdded,
    skillGroupUpdated,
    profileSaved,
} = profileSlice.actions;

export const selectStatus = (state) => state.profile.status;
export const selectLoadError = (state) => state.profile.error;
export const selectProfileExists = (state) => state.profile.exists;
export const selectIdentity = (state) => state.profile.identity;
export const selectExperience = (state) => state.profile.experience;
export const selectEducation = (state) => state.profile.education;
export const selectCertifications = (state) => state.profile.certifications;
export const selectSkillGroups = (state) => state.profile.skillGroups;
export const selectSkillCount = (state) =>
    state.profile.skillGroups.reduce((n, g) => n + g.items.length, 0);
/**
 * Only the personal-details form has a Save button, so only its edits can be unsaved.
 * Every other section writes to the API as you edit it.
 *
 * Derived rather than flagged, so typing a change and undoing it disables Save again.
 */
export const selectDirty = (state) =>
    Boolean(selectAccountChanges(state)) || Boolean(selectProfileChanges(state));

/**
 * The changed subset of `name` and `role` for PATCH /account/updateAccount, or null
 * when neither moved. A PATCH carrying a field the user did not touch is a write the
 * server should never have been asked to make.
 */
export function selectAccountChanges(state) {
    const { identity, saved } = state.profile;
    if (!saved) return null;

    const changes = {};
    for (const field of ACCOUNT_FIELDS) {
        if (identity[field] !== saved[field]) changes[field] = identity[field];
    }
    return Object.keys(changes).length > 0 ? changes : null;
}

/**
 * The changed subset of the profile row for PATCH /profile/updateProfile, or null when
 * nothing moved. `links` is sent whole — a partial list has no meaning.
 */
export function selectProfileChanges(state) {
    const { identity, saved } = state.profile;
    if (!saved) return null;

    const changes = {};
    for (const field of PROFILE_FIELDS) {
        if (!equal(identity[field], saved[field])) changes[field] = identity[field];
    }
    return Object.keys(changes).length > 0 ? changes : null;
}

/** `role` is not here: it belongs to the account, and has its own endpoint. */
export const selectRole = (state) => state.profile.identity.role;

/**
 * The personal-details body for PUT /profile/updateProfile. Experience,
 * education, skills and certifications are their own endpoints, so they are not
 * bundled here. Builds a fresh object, so read it with store.getState() when saving
 * rather than through useSelector.
 *
 * `name` and `email` are absent for the same reason as `role`: the account owns all
 * three, and they are saved through PATCH /account/updateAccount.
 */
export function selectProfilePayload(state) {
    const { identity } = state.profile;
    return {
        headline: identity.headline || null,
        phone: identity.phone || null,
        location: identity.location || null,
        summary: identity.summary || null,
        links: identity.links,
    };
}

export default profileSlice.reducer;
