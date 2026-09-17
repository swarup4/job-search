import { greenhouse } from "@/features/ats/greenhouse";
import { lever } from "@/features/ats/lever";
import { linkedin } from "@/features/ats/linkedin";
import { firstFileInput, type AtsAdapter } from "@/features/ats/types";
import { workday } from "@/features/ats/workday";

export type { AtsAdapter } from "@/features/ats/types";

/** Any career page that is none of the four. The generic engine carries it. */
const generic: AtsAdapter = {
    platform: "other",
    matches: () => true,
    root: (doc) => doc.querySelector("form") ?? doc.body,
    resumeInput: (doc) => firstFileInput(doc),
};

const ADAPTERS = [lever, greenhouse, workday, linkedin];

export function detect(doc: Document = document): AtsAdapter {
    const url = new URL(doc.location.href);
    return ADAPTERS.find((adapter) => adapter.matches(url, doc)) ?? generic;
}
