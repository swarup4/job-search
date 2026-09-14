/**
 * Public interface of the service layer. Screens import from "@/services" and never
 * reach into a file below it.
 */

export { API_URL, ApiError, axiosInstance } from "@/lib/axiosInstance";

export { getJob, listJobs, setShortlisted, updateJob } from "./job";
export { getMatch, getPendingCounts, recordSelection, skipSelection } from "./match";
export { getBaseResume, getResume, listResumeVersions, saveBaseResume } from "./resume";
export { getTemplatePreview, listTemplates, renderTemplate } from "./template";
export {
    getApplication,
    getApplicationForJob,
    listApplications,
    setApplicationStatus,
} from "./application";
export { listEvents } from "./event";
export {
    addCertification,
    addEducation,
    addExperience,
    addSkill,
    createProfile,
    deleteCertification,
    deleteEducation,
    deleteExperience,
    deleteSkill,
    getCertifications,
    getEducation,
    getExperience,
    getProfile,
    getSkills,
    updateCertification,
    updateEducation,
    updateExperience,
    updateProfile,
    updateSkill,
} from "./profile";
export { getShellCounts } from "./shell";
