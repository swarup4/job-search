"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { AlertTriangle, LayoutTemplate, Loader2, RefreshCw, RotateCw } from "lucide-react";

import { ApiError, getBaseResume, renderTemplate, saveBaseResume } from "@/services";
import { Button, buttonVariants } from "@/component/ui/button";
import { Panel, PanelBody } from "@/component/ui/panel";
import { ResumeChat } from "@/component/ResumeChat";
import { ResumeView } from "@/component/ResumeView";
import { toast } from "@/component/ui/toast";
import { ROUTES } from "@/routes";

/**
 * The saved default resume, as it stands.
 *
 * Regenerating re-renders the same template from My Details and stores the result:
 * the profile is what changes between one visit and the next, and the stored `.tex`
 * is a snapshot that does not follow it. That is the point of the button.
 */
export function ResumeReview() {
    const [resume, setResume] = useState(null);
    const [loadError, setLoadError] = useState(null);
    const [attempt, setAttempt] = useState(0);

    const [busy, setBusy] = useState(false);

    const loading = useRef(false);

    useEffect(() => {
        if (loading.current) return;
        loading.current = true;
        setLoadError(null);

        (async () => {
            try {
                setResume(await getBaseResume());
            } catch (failure) {
                setLoadError(
                    failure instanceof ApiError ? failure.message : "Could not load your resume."
                );
            } finally {
                loading.current = false;
            }
        })();
    }, [attempt]);

    async function regenerate() {
        if (!resume) return;
        setBusy(true);
        try {
            const rendered = await renderTemplate(resume.template_id);
            setResume(
                await saveBaseResume({ templateId: resume.template_id, tex: rendered.tex })
            );
            toast.success("Resume regenerated from your latest details.");
        } catch (failure) {
            toast.error(
                failure instanceof ApiError ? failure.message : "Could not regenerate the resume."
            );
        } finally {
            setBusy(false);
        }
    }

    if (loadError) {
        return (
            <Panel>
                <PanelBody className="flex flex-col items-start gap-3 py-8">
                    <Problem>{loadError}</Problem>
                    <Button size="sm" variant="outline" onClick={() => setAttempt((n) => n + 1)}>
                        <RotateCw />
                        Try again
                    </Button>
                </PanelBody>
            </Panel>
        );
    }

    if (resume === null && !loadError) {
        return (
            <Panel>
                <PanelBody className="flex items-center gap-2.5 py-8 text-[13px] text-muted-foreground">
                    <Loader2 className="size-[14px] animate-spin" />
                    Loading your resume…
                </PanelBody>
            </Panel>
        );
    }

    // Loaded, and there is genuinely nothing stored yet.
    if (!resume) {
        return (
            <Panel>
                <PanelBody className="flex flex-col items-start gap-3 py-8">
                    <p className="text-[13px] text-muted-foreground">
                        You have not set a default resume yet.
                    </p>
                    <Link href={ROUTES.resume} className={buttonVariants({ size: "sm" })}>
                        <LayoutTemplate />
                        Pick a template
                    </Link>
                </PanelBody>
            </Panel>
        );
    }

    return (
        <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(360px,420px)]">
            <div className="flex flex-col gap-5">
                <Panel className="p-4">
                    <div className="flex flex-wrap items-center gap-x-5 gap-y-3">
                        <div className="min-w-0">
                            <p className="text-[14px] font-medium">{resume.template_name}</p>
                            <p className="mt-0.5 text-[12.5px] text-muted-foreground">
                                Saved {when(resume.updated_at)}
                            </p>
                        </div>

                        <span className="grow" />

                        {/* One group, so the two buttons wrap together onto the next
                            line rather than splitting across two. */}
                        <div className="flex items-center gap-3">
                            <Link
                                href={ROUTES.resume}
                                className={buttonVariants({ variant: "outline", size: "sm" })}
                            >
                                <LayoutTemplate />
                                Change template
                            </Link>
                            <Button size="sm" onClick={regenerate} disabled={busy}>
                                {busy ? <Loader2 className="animate-spin" /> : <RefreshCw />}
                                Regenerate resume
                            </Button>
                        </div>
                    </div>
                </Panel>

                <ResumeView
                    tex={resume.tex}
                    filename={filenameFor(resume.template_name)}
                    busy={busy}
                    busyLabel="Regenerating from your details…"
                />
            </div>

            <div className="xl:sticky xl:top-6">
                <ResumeChat />
            </div>
        </div>
    );
}

function Problem({ children }) {
    return (
        <p className="flex items-start gap-2 text-[13px] text-risk-ink">
            <AlertTriangle className="mt-0.5 size-[14px] shrink-0" />
            {children}
        </p>
    );
}

/** Mirrors `service.tex_filename` — a download name, not an identifier. */
function filenameFor(name) {
    return `${name.replace(/[^A-Za-z0-9]+/g, "_").replace(/^_|_$/g, "") || "resume"}.tex`;
}

function when(timestamp) {
    return new Date(timestamp).toLocaleString(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
    });
}
