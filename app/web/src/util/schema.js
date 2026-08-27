import * as Yup from "yup";

/**
 * Each form's Yup schema and its initial values, kept side by side: the two must
 * describe the same set of keys, and a field added to one but not the other is the
 * easiest way to get a value Formik never validates.
 *
 * These mirror the server's Pydantic models rather than replacing them — the server
 * validates every request regardless, and its 422 is what decides. Client-side
 * validation exists to answer sooner, not to be trusted.
 */

export const MIN_PASSWORD = 8;

// `email` is required everywhere because the profile document is keyed on it —
// server/modules/profile/models.py makes it the one mandatory field.
const email = Yup.string()
    .trim()
    .required("Enter your email address.")
    .email("That does not look like an email address.");

const name = Yup.string().trim().required("Enter your name.");

// --- sign in -----------------------------------------------------------------

export const loginInitialValues = { email: "", password: "" };

export const loginSchema = Yup.object({
    email,
    password: Yup.string().required("Enter your password."),
});

// --- sign up -----------------------------------------------------------------

export const signupInitialValues = { name: "", email: "", password: "", confirm: "" };

export const signupSchema = Yup.object({
    name,
    email,
    password: Yup.string()
        .required("Enter a password.")
        .min(MIN_PASSWORD, `Use at least ${MIN_PASSWORD} characters for your password.`),
    confirm: Yup.string()
        .required("Type your password again.")
        .oneOf([Yup.ref("password")], "The two passwords do not match."),
});

// --- create the profile (POST /api/profile) ----------------------------------

export const profileCreateInitialValues = { name: "", email: "" };

/** The server requires both of these, so the form does too. */
export const profileCreateSchema = Yup.object({ name, email });

// --- edit the profile (PATCH /api/profile) -----------------------------------

/**
 * A function, not a constant: this form opens on the profile the page already
 * loaded. Every field falls back to "" so the inputs stay controlled — a null from
 * the API would otherwise flip an input to uncontrolled on first render.
 */
export function profileIdentityInitialValues(profile) {
    return {
        name: profile.personal?.name ?? "",
        email: profile.email ?? "",
        headline: profile.personal?.headline ?? "",
        phone: profile.personal?.phone ?? "",
        location: profile.personal?.location ?? "",
        summary: profile.summary ?? "",
        links: profile.personal?.links ?? [],
    };
}

export const profileIdentitySchema = Yup.object({
    name,
    email,
    headline: Yup.string().trim(),
    phone: Yup.string().trim(),
    location: Yup.string().trim(),
    summary: Yup.string().trim(),
    links: Yup.array(
        Yup.object({
            label: Yup.string().trim(),
            value: Yup.string().trim(),
        })
    ),
});
