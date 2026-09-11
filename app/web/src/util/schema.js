import * as Yup from "yup";

export const MIN_PASSWORD = 8;

const email = Yup.string()
    .trim()
    .required("Enter your email address.")
    .email("That does not look like an email address.");

const name = Yup.string().trim().required("Enter your name.");

// sign in

export const loginInitialValues = { email: "", password: "" };

export const loginSchema = Yup.object({
    email,
    password: Yup.string().required("Enter your password."),
});

// sign up

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

// create the profile (POST /api/profile)

export const profileCreateInitialValues = { name: "", email: "" };

/** The server requires both of these, so the form does too. */
export const profileCreateSchema = Yup.object({ name, email });

// the identity fields of the profile, validated on save

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

// one education entry

export function educationInitialValues(entry) {
    return {
        degree: entry?.degree ?? "",
        institution: entry?.institution ?? "",
        location: entry?.location ?? "",
        start: entry?.start ?? "",
        end: entry?.end ?? "",
        note: entry?.note ?? "",
    };
}

export const educationSchema = Yup.object({
    degree: Yup.string().trim().required("Enter the degree or qualification."),
    institution: Yup.string().trim().required("Enter the institution."),
    location: Yup.string().trim(),
    start: Yup.string().trim(),
    end: Yup.string().trim(),
    note: Yup.string().trim(),
});

// one work-experience role

export const MONTHS = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

/** Marks a role still in progress; stored in `end` rather than as a null. */
export const PRESENT = "Present";

export function splitMonthYear(value) {
    const parts = (value ?? "").trim().split(/\s+/);
    if (parts.length === 2 && MONTHS.includes(parts[0])) {
        return { month: parts[0], year: parts[1] };
    }
    if (parts.length === 1 && /^\d{4}$/.test(parts[0])) {
        return { month: "", year: parts[0] };
    }
    return { month: "", year: "" };
}

export function joinMonthYear(month, year) {
    const y = (year ?? "").trim();
    if (!y) return "";
    return month ? `${month} ${y}` : y;
}

export function experienceInitialValues(entry) {
    const start = splitMonthYear(entry?.start);
    const end = splitMonthYear(entry?.end);
    return {
        title: entry?.title ?? "",
        company: entry?.company ?? "",
        location: entry?.location ?? "",
        startMonth: start.month,
        startYear: start.year,
        endMonth: end.month,
        endYear: end.year,
        current: entry?.current ?? false,
        bullets: entry?.bullets?.length ? [...entry.bullets] : [""],
        projects: entry?.projects ?? [],
    };
}

const year = Yup.string()
    .trim()
    .matches(/^\d{4}$/, { message: "Use a four-digit year.", excludeEmptyString: true });

export const experienceSchema = Yup.object({
    title: Yup.string().trim().required("Enter the job title."),
    company: Yup.string().trim().required("Enter the company."),
    location: Yup.string().trim(),
    startMonth: Yup.string(),
    startYear: year,
    endMonth: Yup.string(),
    endYear: year,
    current: Yup.boolean(),
    bullets: Yup.array(Yup.string().trim()),
    projects: Yup.array(
        Yup.object({
            name: Yup.string().trim(),
            bullets: Yup.array(Yup.string().trim()),
        })
    ),
});

// one certification

export function certificationInitialValues(entry) {
    return {
        name: entry?.name ?? "",
        issuer: entry?.issuer ?? "",
        year: entry?.year ?? "",
    };
}

export const certificationSchema = Yup.object({
    name: Yup.string().trim().required("Enter the certification name."),
    issuer: Yup.string().trim().required("Enter the issuer."),
    year: Yup.string()
        .trim()
        .matches(/^\d{4}$/, { message: "Use a four-digit year.", excludeEmptyString: true }),
});

// one skill group

export const skillGroupInitialValues = { name: "" };

/** Group names are the identity in the store, so a new one may not collide. */
export function skillGroupSchema(taken) {
    return Yup.object({
        name: Yup.string()
            .trim()
            .required("Enter a group name.")
            .notOneOf(taken, "That group already exists."),
    });
}
