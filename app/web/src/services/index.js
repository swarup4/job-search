/**
 * Public interface of the service layer. Screens import from "@/services" and never
 * reach into a file below it.
 */

export { AI_URL, API_URL, ApiError, axiosInstance } from "@/lib/axiosInstance";

export { getJob, getJobDetails, listJobs, searchJobs, updateJob } from "./job";
export {
    getMatch,
    getMatchSummaries,
    getUnscoredJobs,
    recordSelection,
    skipSelection,
} from "./match";
export {
    getBaseResume,
    getBaseResumePdf,
    getResume,
    listResumeVersions,
    saveBaseResume,
} from "./resume";
export { getTemplatePreview, listTemplates, renderTemplate } from "./template";
export {
    getApplication,
    getApplicationForJob,
    getBadges,
    getBoardCounts,
    getTracker,
    listApplications,
    listUnstartedJobs,
    setApplicationStatus,
    setShortlisted,
    shortlistJob,
    unshortlistJob,
} from "./application";
export { listEvents } from "./event";
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
export {
    getDiscoveryRun,
    getTierSettings,
    listCareerSources,
    startDiscovery,
    updateCareerSource,
} from "./discovery";
export { getPreferences, savePreferences } from "./preference";
export { getAnalysisRun, startAnalysis } from "./analysis";
export { tailorResume } from "./tailoring";
