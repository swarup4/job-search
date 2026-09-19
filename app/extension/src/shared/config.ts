/** Injected by build.mjs from JOBPILOT_API_URL. */
declare const __API_URL__: string;

export const API_URL = __API_URL__;

/** Both sides enforce it — see `MAX_MARKDOWN_CHARS` on the server. A posting as
 * markdown is a few kilobytes, so this is a backstop, not a working limit. */
export const MAX_MARKDOWN = 400_000;

export const MAX_LINKS = 200;
