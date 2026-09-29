import { axiosInstance } from "@/lib/axiosInstance";

/** GET /api/errorLog — every tier's logged errors, newest first. */
export function getErrorLog(limit = 200) {
    return axiosInstance.get("/errorLog", { params: { limit } });
}

/** DELETE /api/errorLog — empties the shared log file. */
export function clearErrorLog() {
    return axiosInstance.delete("/errorLog");
}
