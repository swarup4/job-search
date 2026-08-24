export const ROUTES = {
    board: "/",
    search: "/search",
    shortlist: "/shortlist",
    job: (jobId) => `/jobs/${jobId}`,
    keywords: (jobId) => `/jobs/${jobId}/keywords`,
    preview: (jobId) => `/jobs/${jobId}/preview`,
    applications: "/applications",
    profile: "/profile",
    settings: "/settings",
};

/** Sidebar IA — single user, so no account or auth items. */
export const NAV = [
    { label: "Pipeline", href: ROUTES.board, icon: "board" },
    { label: "Search jobs", href: ROUTES.search, icon: "search" },
    { label: "Shortlist", href: ROUTES.shortlist, icon: "shortlist", badgeKey: "newJobs" },
    { label: "Applications", href: ROUTES.applications, icon: "applications", badgeKey: "pending" },
    { label: "My details", href: ROUTES.profile, icon: "profile" },
    { label: "Settings", href: ROUTES.settings, icon: "settings" },
];
