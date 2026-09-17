import type { ApplicationRead, AtsPlatform } from "@/shared/types";

/** Which staged application the tab is looking at. Runs in the worker — the
 * content script never sees the pipeline. */

const PLATFORMS: { platform: AtsPlatform; pattern: RegExp }[] = [
    { platform: "lever", pattern: /(^|\.)lever\.co$/ },
    { platform: "greenhouse", pattern: /greenhouse\.io$/ },
    { platform: "workday", pattern: /myworkdayjobs\.com$|myworkdaysite\.com$/ },
    { platform: "linkedin_easy_apply", pattern: /(^|\.)linkedin\.com$/ },
];

export function platformFor(tabUrl: string): AtsPlatform {
    try {
        const { hostname } = new URL(tabUrl);
        return PLATFORMS.find((entry) => entry.pattern.test(hostname))?.platform ?? "other";
    } catch {
        return "other";
    }
}

function parts(raw: string): { host: string; path: string } | null {
    try {
        const url = new URL(raw);
        return { host: url.hostname.replace(/^www\./, ""), path: url.pathname.replace(/\/+$/, "") };
    } catch {
        return null;
    }
}

/** Path segments that appear on every posting of a board and so identify none. */
const GENERIC = new Set([
    "apply",
    "application",
    "applications",
    "form",
    "job",
    "jobs",
    "careers",
    "career",
    "view",
    "en-us",
]);

/**
 * The segment that names the posting: the last one that is not boilerplate. On
 * all four boards that is the slug or the requisition id, which is the only part
 * safe to match on — the company segment is shared by every posting they list.
 */
function postingId(path: string): string | null {
    const segments = path
        .toLowerCase()
        .split("/")
        .filter((segment) => segment && !GENERIC.has(segment));
    return segments[segments.length - 1] ?? null;
}

/**
 * Exact first, then the same posting reached by a slightly different URL — a
 * trailing `/apply`, a tracking query, a `www.`. Below that the host has to match
 * and the posting id has to be the same, because an application attached to the
 * wrong posting is worse than no match at all.
 */
export function matchApplication(
    tabUrl: string,
    applications: ApplicationRead[],
): ApplicationRead | null {
    const tab = parts(tabUrl);
    if (!tab) return null;

    const staged = applications.filter(
        (application): application is ApplicationRead & { applyUrl: string } =>
            application.applyUrl !== null,
    );

    for (const application of staged) {
        if (application.applyUrl === tabUrl) return application;
    }

    for (const application of staged) {
        const apply = parts(application.applyUrl);
        if (!apply || apply.host !== tab.host) continue;
        if (apply.path === tab.path) return application;
        // Only deeper, never shallower: `/acme` is the company's job list, not
        // the posting, and it is a prefix of every posting on it.
        if (tab.path.startsWith(`${apply.path}/`)) return application;
    }

    const wanted = postingId(tab.path);
    if (!wanted || wanted.length < 4) return null;

    for (const application of staged) {
        const apply = parts(application.applyUrl);
        if (!apply || apply.host !== tab.host) continue;
        if (postingId(apply.path) === wanted) return application;
    }

    return null;
}
