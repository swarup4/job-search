import { axiosInstance } from "@/lib/axiosInstance";

/** GET /api/event — newest first. Pass `jobId` for one job's timeline. */
export function listEvents({ jobId, eventType, limit = 100 } = {}) {
    return axiosInstance.get("/event", { params: { job_id: jobId, event_type: eventType, limit } });
}
