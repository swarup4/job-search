"use client";

import { useEffect, useRef, useState } from "react";
import { AlertTriangle, Check, Save, ShieldCheck, Star } from "lucide-react";

import { ApiError, getPreferences, getTierSettings, listLocations, savePreferences } from "@/services";
import { Panel, PanelBody, PanelHeader, PanelTitle } from "@/component/ui/panel";
import { Field, Input } from "@/component/ui/field";
import { TokenInput } from "@/component/ui/token-input";
import { Badge } from "@/component/ui/badge";
import { Button } from "@/component/ui/button";
import { cn } from "@/util/helper";

const WORK_MODES = [
    { value: "on_site", label: "On-site" },
    { value: "hybrid", label: "Hybrid" },
    { value: "remote", label: "Remote" },
];

/** The form's values, in the shape the server stores them. */
function shape(preferences) {
    return {
        roles: preferences.roles,
        skills: preferences.skills ?? [],
        locations: preferences.locations,
        workMode: preferences.workMode ?? null,
        minExperience: preferences.minExperience ?? null,
    };
}

/**
 * What discovery looks for. Saved per account on the API server; Run discovery reads
 * the saved copy when it starts, so the targets a run uses are exactly what this
 * panel showed after Save. Roles and locations filter the scrape; work mode and
 * experience are kept for matching, since job boards rarely publish them in a form
 * worth filtering on.
 */
export function SearchTargets() {
    const [saved, setSaved] = useState(null);
    const [form, setForm] = useState(null);
    const [error, setError] = useState(null);
    const [saving, setSaving] = useState(false);
    const [justSaved, setJustSaved] = useState(false);
    const [places, setPlaces] = useState([]);
    // A ref, not state: React's development double-mount fires the effect twice.
    const loading = useRef(false);

    useEffect(() => {
        if (loading.current) return;
        loading.current = true;
        getPreferences()
            .then((preferences) => {
                setSaved(preferences);
                setForm(shape(preferences));
            })
            .catch((failure) => setError(messageOf(failure, "Could not read your search targets.")));
        // Suggestions only: without them the box still takes anything typed.
        listLocations().then(setPlaces).catch(() => {});
    }, []);

    const dirty = Boolean(form && saved) && JSON.stringify(form) !== JSON.stringify(shape(saved));
    const invalid = form ? problemWith(form) : null;

    function set(field, value) {
        setJustSaved(false);
        setForm((current) => ({ ...current, [field]: value }));
    }

    async function save() {
        setSaving(true);
        setError(null);
        try {
            const stored = await savePreferences(form);
            setSaved(stored);
            setForm(shape(stored));
            setJustSaved(true);
        } catch (failure) {
            setError(messageOf(failure, "Could not save your search targets."));
        } finally {
            setSaving(false);
        }
    }

    return (
        <Panel>
            <PanelHeader>
                <Star className="size-[16px] text-primary" />
                <PanelTitle>Search targets</PanelTitle>
                <span className="grow" />
                {dirty ? <Badge variant="attention">unsaved changes</Badge> : null}
                <Button size="sm" onClick={save} disabled={!dirty || saving || Boolean(invalid)}>
                    {justSaved && !dirty ? <Check /> : <Save />}
                    {saving ? "Saving…" : justSaved && !dirty ? "Saved" : "Save"}
                </Button>
            </PanelHeader>

            <PanelBody className="flex flex-col gap-6 py-5">
                {error ? <Problem message={error} /> : null}

                {!form ? (
                    <p className="text-[13px] text-muted-foreground">reading your search targets…</p>
                ) : (
                    <>
                        <Field
                            label="Target roles"
                            hint="A listing is kept when its title contains one of these as a whole word. Each one is a separate search at every company."
                        >
                            <TokenInput
                                items={form.roles}
                                onChange={(roles) => set("roles", roles)}
                                placeholder="e.g. GenAI Engineer — press Enter to add"
                            />
                        </Field>

                        <Field
                            label="Skills"
                            hint="Optional. A listing is also kept when its description names one of these — for technologies job titles rarely carry, like Node.js or MongoDB. Each one is a separate search, and every result's details are fetched to check, so a run takes longer."
                        >
                            <TokenInput
                                items={form.skills}
                                onChange={(skills) => set("skills", skills)}
                                placeholder="e.g. Node.js — press Enter to add"
                            />
                        </Field>

                        <Field
                            label="Locations"
                            hint="Matched against each posting's country and cities. Include the country (e.g. India) as well as cities, or every company is searched worldwide first."
                        >
                            <TokenInput
                                items={form.locations}
                                onChange={(locations) => set("locations", locations)}
                                suggestions={places}
                                placeholder="e.g. Bengaluru — press Enter to add"
                                tone="muted"
                            />
                        </Field>

                        <div className="grid grid-cols-[minmax(0,1fr)] gap-5 sm:grid-cols-[minmax(0,1fr)_200px]">
                            <Field label="Work mode">
                                <div className="flex flex-wrap gap-2">
                                    {WORK_MODES.map((mode) => {
                                        const on = form.workMode === mode.value;
                                        return (
                                            <button
                                                key={mode.value}
                                                type="button"
                                                aria-pressed={on}
                                                onClick={() => set("workMode", on ? null : mode.value)}
                                                className={cn(
                                                    "rounded-sm px-3 py-1.5 text-[13px] transition-colors",
                                                    on
                                                        ? "bg-primary text-primary-foreground"
                                                        : "bg-secondary text-muted-foreground hover:text-foreground"
                                                )}
                                            >
                                                {mode.label}
                                            </button>
                                        );
                                    })}
                                </div>
                            </Field>
                            <Field label="Min experience (yrs)">
                                <Input
                                    type="number"
                                    min={0}
                                    max={50}
                                    value={form.minExperience ?? ""}
                                    onChange={(event) => set("minExperience", toNumber(event.target.value))}
                                />
                            </Field>
                        </div>

                        <p className="-mt-3 text-[12px] text-muted-foreground">
                            Work mode and experience are saved with your targets for matching. Job boards
                            rarely publish them reliably, so they do not filter the scrape.
                        </p>

                        <p
                            className={cn(
                                "border-t border-border pt-4 text-[12.5px] leading-relaxed",
                                invalid ? "text-risk-ink" : "text-muted-foreground"
                            )}
                        >
                            {invalid ??
                                (dirty
                                    ? "Run discovery uses the saved version — save first to search with these changes."
                                    : saved?.updatedAt
                                      ? `Run discovery searches with these. Saved ${when(saved.updatedAt)}.`
                                      : "These are the defaults. Run discovery searches with them until you save your own.")}
                        </p>
                    </>
                )}
            </PanelBody>
        </Panel>
    );
}

/** Which models see your text, and where they run. Read from the AI tier itself. */
export function ModelsPanel() {
    const [models, setModels] = useState(null);
    const [error, setError] = useState(null);
    const loading = useRef(false);

    useEffect(() => {
        if (loading.current) return;
        loading.current = true;
        getTierSettings()
            .then((settings) => setModels(settings.models))
            .catch((failure) =>
                setError(
                    failure instanceof ApiError && !failure.isOffline && failure.status !== 404
                        ? failure.message
                        : "Start or restart the AI tier (python -m api.main in ai/) to see what it is using."
                )
            );
    }, []);

    return (
        <Panel>
            <PanelHeader>
                <ShieldCheck className="size-[16px] text-primary" />
                <PanelTitle>Models &amp; privacy</PanelTitle>
            </PanelHeader>
            <PanelBody className="flex flex-col gap-4 py-4">
                {error ? <Problem message={error} /> : null}
                <KV label="Generation" value={models?.generation ?? "—"} note="hosted" warn />
                <KV label="Host" value={models?.generationHost ?? "—"} />
                <KV label="Embeddings" value={models?.embeddings ?? "—"} note="hosted" warn />
                <KV label="Rerank" value={models?.rerank ?? "—"} note="hosted" warn />
                <KV label="Eval judge" value="not built yet" />
                <p className="border-t border-border pt-4 text-[12.5px] leading-relaxed text-muted-foreground">
                    Generation and embeddings are hosted: a job description or resume text in a prompt
                    leaves this machine for the model provider. Scraping sends nothing but requests to
                    company job boards.
                </p>
            </PanelBody>
        </Panel>
    );
}

export function KV({ label, value, note, warn }) {
    return (
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <span className="text-[12.5px] text-muted-foreground">{label}</span>
            <span className="grow" />
            <span className="break-all font-mono text-[12.5px]">{value}</span>
            {note ? (
                <Badge variant={warn ? "attention" : "soft"} className="ml-1">
                    {note}
                </Badge>
            ) : null}
        </div>
    );
}

/** The same checks the server makes, so Save is only offered for a form it will take. */
function problemWith(form) {
    if (!form.roles.length) return "Add at least one role — a run needs something to search for.";
    if (!form.locations.length) return "Add at least one location.";
    if (form.minExperience != null && (form.minExperience < 0 || form.minExperience > 50)) {
        return "Min experience must be between 0 and 50.";
    }
    return null;
}

function toNumber(raw) {
    if (raw === "") return null;
    const value = Number.parseInt(raw, 10);
    return Number.isNaN(value) ? null : value;
}

function when(timestamp) {
    return new Date(timestamp).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

function messageOf(failure, fallback) {
    return failure instanceof ApiError ? failure.message : fallback;
}

function Problem({ message }) {
    return (
        <p className="flex items-start gap-1.5 text-[12px] text-risk-ink">
            <AlertTriangle className="mt-0.5 size-[12px] shrink-0" />
            {message}
        </p>
    );
}
