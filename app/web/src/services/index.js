/**
 * Public interface of the service layer. Screens import from "@/services" and never
 * reach into a file below it.
 */

export { AI_URL, API_URL, ApiError, axiosInstance } from "@/lib/axiosInstance";

export { getJob, getJobDetails, listLocations, searchJobs, updateJob } from "./job";
export { getMatch, recordSelection, skipSelection } from "./match";
export {
    getBaseResume,
    getBaseResumePdf,
    getResume,
    saveBaseResume,
} from "./resume";
export { getTemplatePreview, listTemplates, renderTemplate } from "./template";
export {
    getBoard,
    getBoardColumn,
    getShortlist,
    getTracker,
    setApplicationStatus,
    setShortlisted,
    shortlistJob,
    unshortlistJob,
} from "./application";
export { getIndexStats, reindexProfile } from "./retrieval";
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
    getProfile,
    updateCertification,
    updateEducation,
    updateExperience,
    updateProfile,
    updateSkill,
} from "./profile";
export { getStatus } from "./status";
export { getTierSettings, listCareerSources, updateCareerSource } from "./discovery";
export { getPreferences, savePreferences } from "./preference";
export { followRun, startRun } from "./runs";
export { tailorResume } from "./tailoring";
