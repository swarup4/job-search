import { axiosInstance } from "@/lib/axiosInstance";

/** GET /api/template?status=true — the picker's rows. No `.tex`: a listing does not need it. */
export function listTemplates(status = true) {
    return axiosInstance.get("/template", { params: { status } });
}

/** GET /api/template/render/{id} — the signed-in user's profile poured into that template. */
export function renderTemplate(templateId) {
    return axiosInstance.get(`/template/render/${templateId}`);
}

/**
 * The preview PNG as a blob. It cannot be an `<img src>`: the endpoint wants the
 * bearer token, and the browser sends no header on an image request. Callers own
 * the object URL this is turned into, and must revoke it.
 */
export function getTemplatePreview(templateId) {
    return axiosInstance.get(`/template/preview/${templateId}`, { responseType: "blob" });
}
