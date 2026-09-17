/** The API's response shapes, as the `models.py` of each server module defines them. */

export interface Link {
    label: string;
    value: string;
}

export interface AccountRead {
    id: string;
    name: string;
    email: string;
    role: string;
    profilePicture: string | null;
}

export interface LoginResult {
    accessToken: string;
    refreshToken: string;
    account: AccountRead;
}

export interface ProfileRead {
    id: string;
    userId: string;
    headline: string | null;
    phone: string | null;
    location: string | null;
    summary: string | null;
    links: Link[];
}

export interface ExperienceRead {
    id: string;
    title: string;
    company: string;
    location: string | null;
    start: string;
    end: string | null;
    current: boolean;
    bullets: string[];
}

export interface EducationRead {
    id: string;
    degree: string;
    institution: string;
    location: string | null;
    start: string | null;
    end: string | null;
}

export interface SkillRead {
    id: string;
    name: string;
    items: string[];
}

export interface CertificationRead {
    id: string;
    name: string;
    issuer: string;
    year: string | null;
}

export interface UserProfile {
    id: string;
    name: string;
    email: string;
    role: string;
    profilePicture: string | null;
    profile: ProfileRead | null;
    work: ExperienceRead[];
    education: EducationRead[];
    skill: SkillRead[];
    certification: CertificationRead[];
}

export interface AnswerBankEntry {
    key: string;
    question: string;
    answer: string;
    tags: string[];
    usedCount: number;
}

export type AtsPlatform = "workday" | "greenhouse" | "lever" | "linkedin_easy_apply" | "other";

export type ApplicationStatus =
    | "staged"
    | "applied"
    | "viewed"
    | "interview"
    | "offer"
    | "rejected"
    | "withdrawn";

/** FR-5.4 — what went into one field, and where the value came from. */
export interface FieldFill {
    selector: string;
    label: string;
    value: string;
    source: "profile" | "answer_bank" | "llm_fallback";
    highlighted: boolean;
}

export interface ScreeningAnswer {
    question: string;
    answer: string | null;
    answeredByUser: boolean;
}

export interface ApplicationRead {
    id: string;
    jobId: string;
    resumeId: string;
    texPath: string;
    ats: AtsPlatform;
    applyUrl: string | null;
    status: ApplicationStatus;
    fieldsFilled: FieldFill[];
    screeningAnswers: ScreeningAnswer[];
    approvedByUser: boolean;
    stagedAt: string;
    submittedAt: string | null;
    needs_answer: number;
}

export interface Company {
    name: string;
    industry: string | null;
    site: string | null;
}

export interface JobRead {
    id: string;
    title: string;
    company: Company;
    location: string;
    workMode: string | null;
    salaryText: string | null;
    status: string;
}
