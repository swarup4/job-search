import { lookup } from "@/features/answerBank";
import type { ScannedField } from "@/features/fieldFill/scan";
import type { AnswerBankEntry, UserProfile } from "@/shared/types";

/**
 * The question a field is asking, named. Anything not on this list, and anything
 * on it with nothing in the profile to answer it, becomes a pending question —
 * never a guess. The profile holds no cover letter, work authorisation or EEO
 * data, so those resolve from the answer bank alone.
 */
export type AnswerKey =
    | "firstName"
    | "lastName"
    | "fullName"
    | "email"
    | "phone"
    | "location"
    | "linkedin"
    | "github"
    | "portfolio"
    | "currentCompany"
    | "currentTitle"
    | "headline"
    | "summary"
    | "coverLetter"
    | "school"
    | "degree"
    | "fieldOfStudy"
    | "gradYear"
    | "yearsExperience"
    | "noticePeriod"
    | "currentSalary"
    | "expectedSalary"
    | "workAuthorization"
    | "sponsorship"
    | "relocate"
    | "startDate"
    | "howHeard"
    | "referral"
    | "gender"
    | "race"
    | "veteran"
    | "disability";

/** Ordered: the first pattern that matches wins, so narrow questions are listed
 * ahead of the broad ones they would otherwise be swallowed by. */
const RULES: { key: AnswerKey; patterns: RegExp[] }[] = [
    { key: "lastName", patterns: [/^(last|family|sur)\s?name$/, /\blast name\b/, /\bsurname\b/] },
    { key: "firstName", patterns: [/^(first|given|fore)\s?name$/, /\bfirst name\b/, /\bgiven name\b/] },
    { key: "fullName", patterns: [/^(full |your |legal |candidate |applicant )?name$/, /\bfull name\b/] },
    { key: "email", patterns: [/\be-?mail\b/] },
    { key: "phone", patterns: [/\b(phone|mobile|cell|telephone)\b/, /\bcontact number\b/] },
    { key: "linkedin", patterns: [/\blinked ?in\b/] },
    { key: "github", patterns: [/\bgit ?hub\b/] },
    { key: "portfolio", patterns: [/\b(portfolio|personal (site|website)|website|blog)\b/] },
    { key: "expectedSalary", patterns: [/\b(expected|desired|target)\b.*\b(salary|ctc|compensation|pay)\b/] },
    { key: "currentSalary", patterns: [/\b(current|present)\b.*\b(salary|ctc|compensation|pay)\b/, /^(salary|ctc)$/] },
    { key: "noticePeriod", patterns: [/\bnotice period\b/, /\bnotice\b/] },
    { key: "currentCompany", patterns: [/\b(current|present|recent)\b.*\b(company|employer|organi[sz]ation)\b/, /^(company|employer|organi[sz]ation)( name)?$/] },
    { key: "currentTitle", patterns: [/\b(current|present|recent)\b.*\b(title|role|position|designation)\b/, /^(job )?(title|role|position|designation)$/] },
    { key: "headline", patterns: [/\bheadline\b/] },
    { key: "coverLetter", patterns: [/\bcover letter\b/, /\bwhy do you want\b/, /\bwhy are you interested\b/] },
    { key: "summary", patterns: [/\b(summary|about (you|yourself)|tell us about)\b/, /\badditional information\b/] },
    { key: "fieldOfStudy", patterns: [/\b(field of study|major|discipline|speciali[sz]ation|stream)\b/] },
    { key: "degree", patterns: [/\bdegree\b/, /\bqualification\b/] },
    { key: "school", patterns: [/\b(school|university|college|institution|institute)\b/] },
    { key: "gradYear", patterns: [/\b(graduation|grad)\b.*\b(year|date)\b/, /\byear of (graduation|passing)\b/] },
    { key: "yearsExperience", patterns: [/\b(years|yrs)\b.{0,16}\bexperience\b/, /\b(total|overall) experience\b/] },
    { key: "sponsorship", patterns: [/\bsponsor(ship)?\b/, /\bvisa\b/] },
    { key: "workAuthorization", patterns: [/\b(work authori[sz]ation|authori[sz]ed to work|right to work|work permit|legally (able|authori[sz]ed))\b/] },
    { key: "relocate", patterns: [/\brelocat/] },
    { key: "startDate", patterns: [/\b(start date|earliest start|available|availability|when can you)\b/, /\bjoining date\b/] },
    { key: "howHeard", patterns: [/\bhow did you (hear|find|learn)\b/, /\b(how|where) did you hear about\b/] },
    { key: "referral", patterns: [/\brefer(r?al|red by)\b/] },
    { key: "gender", patterns: [/\bgender\b/] },
    { key: "race", patterns: [/\b(race|ethnicity|hispanic|latino)\b/] },
    { key: "veteran", patterns: [/\bveteran\b/, /\bmilitary\b/] },
    { key: "disability", patterns: [/\bdisabilit/] },
    { key: "location", patterns: [/\b(location|city|town|address|based)\b/, /\bwhere are you\b/] },
];

export function canonicalKey(fieldKey: string): AnswerKey | null {
    for (const rule of RULES) {
        if (rule.patterns.some((pattern) => pattern.test(fieldKey))) return rule.key;
    }
    return null;
}

function currentRole(profile: UserProfile) {
    return profile.work.find((role) => role.current) ?? profile.work[0] ?? null;
}

function linkMatching(profile: UserProfile, pattern: RegExp): string | null {
    const link = profile.profile?.links.find(
        (candidate) => pattern.test(candidate.label) || pattern.test(candidate.value),
    );
    return link?.value ?? null;
}

function nameParts(name: string): { first: string | null; last: string | null } {
    const parts = name.trim().split(/\s+/).filter(Boolean);
    if (parts.length === 0) return { first: null, last: null };
    if (parts.length === 1) return { first: parts[0] ?? null, last: null };
    return { first: parts[0] ?? null, last: parts[parts.length - 1] ?? null };
}

/** What the profile can answer on its own. `null` means the profile does not
 * hold it, which is a pending question rather than something to improvise. */
export function fromProfile(key: AnswerKey, profile: UserProfile): string | null {
    const details = profile.profile;
    const role = currentRole(profile);
    const school = profile.education[0] ?? null;

    switch (key) {
        case "fullName":
            return profile.name || null;
        case "firstName":
            return nameParts(profile.name).first;
        case "lastName":
            return nameParts(profile.name).last;
        case "email":
            return profile.email || null;
        case "phone":
            return details?.phone ?? null;
        case "location":
            return details?.location ?? null;
        case "headline":
            return details?.headline ?? profile.role ?? null;
        case "summary":
            return details?.summary ?? null;
        case "linkedin":
            return linkMatching(profile, /linked ?in/i);
        case "github":
            return linkMatching(profile, /git ?hub/i);
        case "portfolio":
            return linkMatching(profile, /portfolio|website|\.dev|\.me|blog/i);
        case "currentCompany":
            return role?.company ?? null;
        case "currentTitle":
            return role?.title ?? null;
        case "school":
            return school?.institution ?? null;
        case "degree":
            return school?.degree ?? null;
        case "gradYear":
            return /\b(19|20)\d{2}\b/.exec(school?.end ?? "")?.[0] ?? null;
        default:
            return null;
    }
}

export interface Resolution {
    value: string;
    source: "profile" | "answer_bank";
    key: AnswerKey | null;
}

/**
 * An exact answer-bank hit outranks the profile — the user wrote it for this
 * question. A fuzzy hit ranks below, so "location" does not lose to a stored
 * answer that merely shares words with it.
 */
export function resolve(
    field: ScannedField,
    profile: UserProfile,
    bank: AnswerBankEntry[],
): Resolution | null {
    const key = canonicalKey(field.key);

    const match = lookup(bank, field.key, key);
    if (match?.exact) return { value: match.entry.answer, source: "answer_bank", key };

    if (key) {
        const value = fromProfile(key, profile);
        if (value) return { value, source: "profile", key };
    }

    if (match) return { value: match.entry.answer, source: "answer_bank", key };

    return null;
}
