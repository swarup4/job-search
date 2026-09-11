"use client";

import { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useFormik } from "formik";
import { Briefcase, Building2, FolderGit2, Pencil, Plus, X } from "lucide-react";
import { Panel, PanelHeader, PanelTitle } from "@/component/ui/panel";
import { Dialog, DialogBody, DialogFooter } from "@/component/ui/dialog";
import { Field, Input, Select } from "@/component/ui/field";
import { Checkbox } from "@/component/ui/checkbox";
import { Button } from "@/component/ui/button";
import { Badge } from "@/component/ui/badge";
import {
    roleAdded,
    roleProjectsSet,
    roleUpdated,
    selectExperience,
} from "@/store/profile/profileSlice";
import {
    MONTHS,
    PRESENT,
    experienceInitialValues,
    experienceSchema,
    joinMonthYear,
} from "@/util/schema";
import { cn } from "@/util/cn";

export function ExperienceSection() {
    const roles = useSelector(selectExperience);
    const dispatch = useDispatch();
    // null = closed. { entry: null } = adding; { entry } = editing that one.
    const [editing, setEditing] = useState(null);
    // The role whose projects are open, or null.
    const [managing, setManaging] = useState(null);

    function commit(values) {
        const entry = {
            title: values.title,
            company: values.company,
            location: values.location,
            start: joinMonthYear(values.startMonth, values.startYear),
            end: values.current ? PRESENT : joinMonthYear(values.endMonth, values.endYear),
            current: values.current,
            // Drop the blank rows the form leaves behind before they reach the list.
            bullets: values.bullets.map((b) => b.trim()).filter(Boolean),
            // Carried through untouched: projects are owned by the other dialog.
            projects: values.projects,
        };
        dispatch(
            editing.entry
                ? roleUpdated({ id: editing.entry.id, changes: entry })
                : roleAdded(entry)
        );
        setEditing(null);
    }

    function commitProjects(projects) {
        dispatch(roleProjectsSet({ id: managing.id, projects }));
        setManaging(null);
    }

    return (
        <Panel>
            <PanelHeader>
                <Briefcase className="size-[16px] text-primary" />
                <PanelTitle>Work experience</PanelTitle>
                <Badge variant="soft">{roles.length}</Badge>
                <span className="grow" />
                <button
                    type="button"
                    onClick={() => setEditing({ entry: null })}
                    className="inline-flex items-center gap-1.5 text-[13px] font-medium text-primary hover:underline"
                >
                    <Plus className="size-[14px]" />
                    Add role
                </button>
            </PanelHeader>

            <div>
                {roles.length === 0 ? (
                    <p className="px-5 py-6 text-[13.5px] text-muted-foreground">
                        No roles yet. Add one so tailoring has experience to draw on.
                    </p>
                ) : (
                    roles.map((job, i) => (
                        <div
                            key={job.id}
                            className={cn("px-5 py-5", i < roles.length - 1 && "border-b border-border")}
                        >
                            <div className="flex flex-wrap items-start gap-4 sm:flex-nowrap">
                                <span className="grid size-11 shrink-0 place-items-center rounded-md bg-secondary text-muted-foreground">
                                    <Building2 className="size-[18px]" />
                                </span>
                                <div className="min-w-0 grow">
                                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                                        <h3 className="text-[15.5px] font-medium">{job.title}</h3>
                                        {job.current ? <Badge variant="soft">current</Badge> : null}
                                    </div>
                                    <p className="mt-1 text-[13.5px] text-muted-foreground">
                                        {job.company}
                                        {job.location ? ` · ${job.location}` : ""}
                                    </p>
                                    <p className="mt-0.5 text-[12.5px] text-muted-foreground">
                                        {job.start} — {job.end}
                                    </p>
                                    <ul className="mt-3 flex flex-col gap-2">
                                        {job.bullets.map((b, bi) => (
                                            <li
                                                key={bi}
                                                className="flex gap-2.5 text-[13.5px] leading-relaxed"
                                            >
                                                <span className="mt-[7px] size-1.5 shrink-0 rounded-full bg-primary" />
                                                <span className="text-muted-foreground">{b}</span>
                                            </li>
                                        ))}
                                    </ul>

                                    {job.projects?.length ? (
                                        <div className="mt-4 flex flex-col gap-2">
                                            {job.projects.map((project, pi) => (
                                                <div key={pi} className="rounded-sm bg-well px-4 py-3">
                                                    <p className="flex items-center gap-2 text-[13px] font-semibold">
                                                        <FolderGit2 className="size-[13px] shrink-0 text-primary" />
                                                        {project.name}
                                                    </p>
                                                    <ul className="mt-2 flex flex-col gap-1.5">
                                                        {project.bullets.map((b, bi) => (
                                                            <li
                                                                key={bi}
                                                                className="flex gap-2.5 text-[13px] leading-relaxed"
                                                            >
                                                                <span className="mt-[7px] size-1 shrink-0 rounded-full bg-primary" />
                                                                <span className="text-muted-foreground">{b}</span>
                                                            </li>
                                                        ))}
                                                    </ul>
                                                </div>
                                            ))}
                                        </div>
                                    ) : null}
                                </div>

                                <div className="flex shrink-0 flex-col items-stretch gap-1">
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        onClick={() => setEditing({ entry: job })}
                                    >
                                        <Pencil />
                                        Edit
                                    </Button>
                                    {job.current || job.projects?.length ? (
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            onClick={() => setManaging(job)}
                                        >
                                            <FolderGit2 />
                                            Project
                                            {job.projects?.length ? ` (${job.projects.length})` : ""}
                                        </Button>
                                    ) : null}
                                </div>
                            </div>
                        </div>
                    ))
                )}
            </div>

            {editing ? (
                <Dialog
                    open
                    onClose={() => setEditing(null)}
                    title={editing.entry ? "Edit role" : "Add role"}
                    description="Only the title and company are required."
                >
                    <ExperienceForm
                        entry={editing.entry}
                        onSave={commit}
                        onCancel={() => setEditing(null)}
                    />
                </Dialog>
            ) : null}

            {managing ? (
                <Dialog
                    open
                    onClose={() => setManaging(null)}
                    title="Projects"
                    description={`${managing.title} · ${managing.company}`}
                >
                    <ProjectsForm
                        projects={managing.projects}
                        onSave={commitProjects}
                        onCancel={() => setManaging(null)}
                    />
                </Dialog>
            ) : null}
        </Panel>
    );
}

function ExperienceForm({ entry, onSave, onCancel }) {
    const formik = useFormik({
        initialValues: experienceInitialValues(entry),
        validationSchema: experienceSchema,
        onSubmit: onSave,
    });

    const { values, touched, errors, setFieldValue } = formik;
    const error = (key) => touched[key] && errors[key];

    return (
        <form onSubmit={formik.handleSubmit} noValidate>
            <DialogBody className="flex flex-col gap-5">
                <Field label="Job title" error={error("title")}>
                    <Input
                        autoFocus
                        placeholder="Senior Backend Engineer"
                        invalid={Boolean(error("title"))}
                        {...formik.getFieldProps("title")}
                    />
                </Field>

                <div className="grid gap-5 sm:grid-cols-2">
                    <Field label="Company" error={error("company")}>
                        <Input
                            placeholder="Acme Corp"
                            invalid={Boolean(error("company"))}
                            {...formik.getFieldProps("company")}
                        />
                    </Field>

                    <Field label="Location">
                        <Input placeholder="Bengaluru" {...formik.getFieldProps("location")} />
                    </Field>
                </div>

                <div className="grid gap-5 sm:grid-cols-2">
                    <Field label="Start" error={error("startYear")}>
                        <div className="flex gap-2.5">
                            <Select className="w-[104px]" {...formik.getFieldProps("startMonth")}>
                                <option value="">Month</option>
                                {MONTHS.map((m) => (
                                    <option key={m} value={m}>{m}</option>
                                ))}
                            </Select>
                            <Input
                                placeholder="2021"
                                inputMode="numeric"
                                invalid={Boolean(error("startYear"))}
                                {...formik.getFieldProps("startYear")}
                            />
                        </div>
                    </Field>

                    <Field
                        label="End"
                        error={error("endYear")}
                        hint={values.current ? "Shown as “Present” while this role is current." : undefined}
                    >
                        <div className={cn("flex gap-2.5", values.current && "opacity-45")}>
                            <Select
                                className="w-[104px]"
                                disabled={values.current}
                                {...formik.getFieldProps("endMonth")}
                            >
                                <option value="">Month</option>
                                {MONTHS.map((m) => (
                                    <option key={m} value={m}>{m}</option>
                                ))}
                            </Select>
                            <Input
                                placeholder="2024"
                                inputMode="numeric"
                                disabled={values.current}
                                invalid={Boolean(error("endYear"))}
                                {...formik.getFieldProps("endYear")}
                            />
                        </div>
                    </Field>
                </div>

                <label className="flex w-fit cursor-pointer items-center gap-2.5">
                    <Checkbox
                        checked={values.current}
                        onCheckedChange={(next) => setFieldValue("current", next)}
                    />
                    <span className="text-[13px]">I currently work here</span>
                </label>

                <BulletList
                    label="Description"
                    hint="One line per achievement. A number carries more weight than an adjective."
                    bullets={values.bullets}
                    onChange={(next) => setFieldValue("bullets", next)}
                    placeholder="Cut inference cost 38% through batching"
                    removeLabel={(i) => `Remove description line ${i + 1}`}
                />
            </DialogBody>

            <DialogFooter>
                <Button type="button" variant="outline" size="sm" onClick={onCancel}>
                    Cancel
                </Button>
                <Button type="submit" size="sm">
                    {entry ? "Save changes" : "Add role"}
                </Button>
            </DialogFooter>
        </form>
    );
}

/** Every project on one role: a name plus its own description lines. */
function ProjectsForm({ projects, onSave, onCancel }) {
    const formik = useFormik({
        initialValues: {
            projects: (projects ?? []).map((p) => ({
                name: p.name ?? "",
                bullets: p.bullets?.length ? [...p.bullets] : [""],
            })),
        },
        onSubmit: (values) =>
            onSave(
                values.projects
                    .map((p) => ({
                        name: p.name.trim(),
                        bullets: p.bullets.map((b) => b.trim()).filter(Boolean),
                    }))
                    // A project with no name has nothing to render, so it is not kept.
                    .filter((p) => p.name)
            ),
    });

    const { values, setFieldValue } = formik;
    const setProjects = (next) => setFieldValue("projects", next);
    const patchProject = (index, patch) =>
        setProjects(values.projects.map((p, i) => (i === index ? { ...p, ...patch } : p)));

    return (
        <form onSubmit={formik.handleSubmit} noValidate>
            <DialogBody className="flex flex-col gap-4">
                {values.projects.length === 0 ? (
                    <p className="text-[13.5px] text-muted-foreground">
                        No projects on this role yet.
                    </p>
                ) : (
                    values.projects.map((project, i) => (
                        <div key={i} className="rounded-sm bg-well p-4">
                            <div className="flex items-center gap-2.5">
                                <Input
                                    autoFocus={i === 0}
                                    placeholder="Project name"
                                    value={project.name}
                                    onChange={(event) => patchProject(i, { name: event.target.value })}
                                />
                                <button
                                    type="button"
                                    aria-label={`Remove project ${i + 1}`}
                                    onClick={() =>
                                        setProjects(values.projects.filter((_, pi) => pi !== i))
                                    }
                                    className="grid size-8 shrink-0 place-items-center rounded-sm text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
                                >
                                    <X className="size-[14px]" />
                                </button>
                            </div>

                            <div className="mt-3">
                                <BulletList
                                    label="Description"
                                    bullets={project.bullets}
                                    onChange={(next) => patchProject(i, { bullets: next })}
                                    placeholder="What this project delivered"
                                    removeLabel={(bi) => `Remove project ${i + 1} line ${bi + 1}`}
                                />
                            </div>
                        </div>
                    ))
                )}

                <button
                    type="button"
                    onClick={() => setProjects([...values.projects, { name: "", bullets: [""] }])}
                    className="inline-flex w-fit items-center gap-1.5 text-[13px] font-medium text-primary hover:underline"
                >
                    <Plus className="size-[14px]" />
                    Add project
                </button>
            </DialogBody>

            <DialogFooter>
                <Button type="button" variant="outline" size="sm" onClick={onCancel}>
                    Cancel
                </Button>
                <Button type="submit" size="sm">
                    Save projects
                </Button>
            </DialogFooter>
        </form>
    );
}

/** The add/remove line editor, shared by the role and by each of its projects. */
function BulletList({
    label,
    hint,
    bullets,
    onChange,
    placeholder,
    addLabel = "Add line",
    removeLabel,
}) {
    return (
        <div>
            <p className="mb-1 text-[13px] font-medium">{label}</p>
            {hint ? <p className="mb-2.5 text-[12px] text-muted-foreground">{hint}</p> : null}
            <div className="flex flex-col gap-3">
                {bullets.map((bullet, i) => (
                    <div key={i} className="flex items-center gap-2.5">
                        <Input
                            placeholder={placeholder}
                            value={bullet}
                            onChange={(event) =>
                                onChange(bullets.map((b, bi) => (bi === i ? event.target.value : b)))
                            }
                        />
                        <button
                            type="button"
                            aria-label={removeLabel(i)}
                            onClick={() =>
                                onChange(
                                    bullets.length === 1 ? [""] : bullets.filter((_, bi) => bi !== i)
                                )
                            }
                            className="grid size-8 shrink-0 place-items-center rounded-sm text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
                        >
                            <X className="size-[14px]" />
                        </button>
                    </div>
                ))}
                <button
                    type="button"
                    onClick={() => onChange([...bullets, ""])}
                    className="inline-flex w-fit items-center gap-1.5 text-[13px] font-medium text-primary hover:underline"
                >
                    <Plus className="size-[14px]" />
                    {addLabel}
                </button>
            </div>
        </div>
    );
}
