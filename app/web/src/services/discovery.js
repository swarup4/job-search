import { aiInstance, axiosInstance } from "@/lib/axiosInstance";

/**
 * Career-page scraping. The company list lives on the API server; a run is started
 * on the AI tier, which scrapes as the signed-in user with the token forwarded on
 * the request.
 */

/** GET /api/career-source — every registered company with its last run's result. */
export function listCareerSources() {
    return axiosInstance.get("/career-source");
}

/** PATCH /api/career-source/{id} — today only `enabled`, from the Sources toggles. */
export function updateCareerSource(sourceId, changes) {
    return axiosInstance.patch(`/career-source/${sourceId}`, changes);
}

/** GET /api/settings on the AI tier — the scrape filter and models actually in use. */
export function getTierSettings() {
    return aiInstance.get("/settings");
}

/** POST /api/discovery/run on the AI tier. 409 while a run is already going. */
export function startDiscovery() {
    return aiInstance.post("/discovery/run");
}

/** GET /api/discovery/run on the AI tier — the latest run, or null if there is none. */
export function getDiscoveryRun() {
    return aiInstance.get("/discovery/run");
}
