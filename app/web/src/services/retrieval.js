import { axiosInstance } from "@/lib/axiosInstance";

/**
 * The retrieval index built from My Details. Like the profile calls, neither takes a
 * user id: the server reads it from the bearer token.
 */

/** `{ chunks, embedded, pending, lastIndexedAt }`. */
export function getIndexStats() {
    return axiosInstance.get("/resume-chunk/stats");
}

/**
 * Re-cut the profile into chunks and return the same stats.
 *
 * Text only: the server does not embed anything, so this leaves the changed chunks
 * `pending` and the AI tier gives them vectors on its next run. That is why the
 * panel shows pending as its own number rather than folding it into the total — an
 * unembedded chunk is not retrievable yet, and saying otherwise would be a claim
 * about the index that is not true.
 */
export function reindexProfile() {
    return axiosInstance.post("/profile/reindex");
}
