export const ROUTES = {
  board: "/",
  search: "/search",
  shortlist: "/shortlist",
  applications: "/applications",
  profile: "/profile",
  settings: "/settings",

  // Pre-auth screens. Deliberately absent from NAV — they are not sidebar
  // destinations, and the docs specify no accounts (PRD §4).
  login: "/login",
  signup: "/signup",

  // `from` records which section the user came from, so the sidebar keeps that
  // section highlighted while they drill into a job. Without it a job opened
  // from Search would light up Shortlist (or nothing).
  job: (id, from) => withFrom(`/jobs/${id}`, from),
  keywords: (id, from) => withFrom(`/jobs/${id}/keywords`, from),
  preview: (id, from) => withFrom(`/jobs/${id}/preview`, from),
};

function withFrom(path, from) {
  return from ? `${path}?from=${from}` : path;
}

/** Map a `from` value back to the sidebar entry that should stay highlighted. */
export const SECTION = {
  search: ROUTES.search,
  shortlist: ROUTES.shortlist,
  board: ROUTES.board,
  applications: ROUTES.applications,
};

export function sectionFor(from) {
  return SECTION[from] ?? ROUTES.search;
}

export const NAV = [
  { label: "Pipeline", href: ROUTES.board, icon: "board" },
  { label: "Search jobs", href: ROUTES.search, icon: "search" },
  { label: "Shortlist", href: ROUTES.shortlist, icon: "shortlist", badgeKey: "shortlisted" },
  { label: "Applications", href: ROUTES.applications, icon: "applications", badgeKey: "pending" },
  { label: "My details", href: ROUTES.profile, icon: "profile" },
  { label: "Settings", href: ROUTES.settings, icon: "settings" },
];
