"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AlertTriangle, ArrowRight, Check, Loader2, RotateCw } from "lucide-react";

import {
    ApiError,
    getBaseResume,
    listTemplates,
    renderTemplate,
    saveBaseResume,
} from "@/services";
import { Button, buttonVariants } from "@/component/ui/button";
import { Panel, PanelBody, PanelHeader, PanelTitle } from "@/component/ui/panel";
import { toast } from "@/component/ui/toast";
import { TemplatePicker } from "@/component/TemplatePicker";
import { ROUTES } from "@/routes";

/**
 * Picking the template the default resume is built from.
 *
 * The document itself is not shown here — the review screen is where it is read, and
 * showing it twice invited the two to disagree. The render still runs on every
 * selection, because its `.tex` is what Submit sends.
 *
 * The fetching is here rather than in the page because the bearer token lives in
 * sessionStorage, which the server-rendered page cannot read.
 *
 * What is submitted is the `.tex` exactly as the server rendered it, so the document
 * stored is the one a tailoring run starts from.
 *
 * Submitting moves on to the review screen: the decision this screen exists for has
 * been made, and what comes next is living with the result.
 */
export function ResumeBuilder() {
    const [templates, setTemplates] = useState(null);
    const [saved, setSaved] = useState(null);
    const [loadError, setLoadError] = useState(null);
    const [attempt, setAttempt] = useState(0);

    const [selected, setSelected] = useState(null);
    const [render, setRender] = useState(null);
    const [rendering, setRendering] = useState(false);
    const [renderError, setRenderError] = useState(null);

    const [saving, setSaving] = useState(false);

    const router = useRouter();
    const loading = useRef(false);

    useEffect(() => {
        if (loading.current) return;
        loading.current = true;
        setLoadError(null);

        (async () => {
            try {
                const [rows, base] = await Promise.all([listTemplates(), getBaseResume()]);
                setTemplates(rows);
                setSaved(base);
                // Reopening the screen lands on the template already in use.
                setSelected(base?.templateId ?? rows[0]?.id ?? null);
            } catch (failure) {
                setLoadError(
                    failure instanceof ApiError ? failure.message : "Could not load templates."
                );
            } finally {
                loading.current = false;
            }
        })();
    }, [attempt]);

    // Every selection renders, including the first — the preview is the whole point
    // of the screen, so there is nothing to press to see it.
    useEffect(() => {
        if (!selected) return undefined;

        let cancelled = false;
        setRendering(true);
        setRenderError(null);

        renderTemplate(selected)
            .then((result) => {
                if (!cancelled) setRender(result);
            })
            .catch((failure) => {
                if (cancelled) return;
                setRender(null);
                setRenderError(
                    failure instanceof ApiError
                        ? failure.message
                        : "Could not render this template."
                );
            })
            .finally(() => {
                if (!cancelled) setRendering(false);
            });

        return () => {
            cancelled = true;
        };
    }, [selected]);

    // Nothing to submit when the stored .tex is already character-for-character this one.
    const unchanged = saved?.templateId === selected && saved?.tex === render?.tex;

    async function submit() {
        if (!render) return;
        setSaving(true);
        try {
            await saveBaseResume({ templateId: selected, tex: render.tex });
            // The toast outlives the navigation — it is mounted in the root layout —
            // so the confirmation arrives on the screen the user lands on.
            toast.success("Saved as your default resume.");
            router.push(ROUTES.resumePreview);
            // `saving` is left set: the button stays busy until the next screen
            // paints, rather than flicking back to idle mid-navigation.
        } catch (failure) {
            toast.error(
                failure instanceof ApiError ? failure.message : "Could not save the resume."
            );
            setSaving(false);
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

    if (!templates) {
        return (
            <Panel>
                <PanelBody className="flex items-center gap-2.5 py-8 text-[13px] text-muted-foreground">
                    <Loader2 className="size-[14px] animate-spin" />
                    Loading templates…
                </PanelBody>
            </Panel>
        );
    }

    if (!templates.length) {
        return (
            <Panel>
                <PanelBody className="py-8 text-[13px] text-muted-foreground">
                    No templates have been uploaded yet. Add one with{" "}
                    <span className="font-mono text-[12px]">POST /api/template/upload</span> and it
                    will appear here.
                </PanelBody>
            </Panel>
        );
    }

    return (
        <div className="flex flex-col gap-5">
            <Panel>
                <PanelHeader>
                    <PanelTitle>Resume template</PanelTitle>
                    <span className="grow" />
                    <span className="text-[12.5px] text-muted-foreground">
                        {saved
                            ? `Preference: ${saved.templateName}`
                            : "No default resume yet"}
                    </span>
                </PanelHeader>
                <PanelBody className="py-5">
                    <TemplatePicker
                        templates={templates}
                        selected={selected}
                        preferred={saved?.templateId ?? null}
                        onSelect={setSelected}
                        disabled={saving}
                    />
                </PanelBody>
            </Panel>

            <Panel className="p-4">
                <div className="flex flex-wrap items-center gap-x-5 gap-y-3">
                    <div className="min-w-[240px]">
                        <p className="text-[14px] font-medium">
                            {saved ? "Your default resume" : "Set your default resume"}
                        </p>
                        <p className="mt-0.5 text-[12.5px] text-muted-foreground">
                            {saved
                                ? `Stored from ${saved.templateName} · updated ${when(saved.updatedAt)}`
                                : "Submitting stores this .tex as the resume every tailored version starts from."}
                        </p>
                    </div>

                    <span className="grow" />

                    {/* The render is no longer on screen, so its state is reported
                        here — it is what the button submits. */}
                    {renderError ? <Problem>{renderError}</Problem> : null}
                    {rendering && !renderError ? (
                        <span className="inline-flex items-center gap-1.5 text-[13px] text-muted-foreground">
                            <Loader2 className="size-4 animate-spin" />
                            Preparing this template…
                        </span>
                    ) : null}

                    {unchanged ? (
                        <>
                            <span className="inline-flex items-center gap-1.5 text-[13px] text-primary">
                                <Check className="size-4" />
                                Saved
                            </span>
                            <Link
                                href={ROUTES.resumePreview}
                                className={buttonVariants({ variant: "outline", size: "sm" })}
                            >
                                View resume
                                <ArrowRight />
                            </Link>
                        </>
                    ) : (
                        <Button size="sm" onClick={submit} disabled={!render || rendering || saving}>
                            {saving ? <Loader2 className="animate-spin" /> : <Check />}
                            {saved ? "Replace default resume" : "Submit as default resume"}
                        </Button>
                    )}
                </div>
            </Panel>
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

function when(timestamp) {
    return new Date(timestamp).toLocaleString(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
    });
}
