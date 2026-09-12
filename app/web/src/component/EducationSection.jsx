"use client";

import { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useFormik } from "formik";
import { GraduationCap, Pencil, Plus } from "lucide-react";
import { Panel, PanelHeader, PanelTitle } from "@/component/ui/panel";
import { Dialog, DialogBody, DialogFooter } from "@/component/ui/dialog";
import { Field, Input } from "@/component/ui/field";
import { Button } from "@/component/ui/button";
import { Badge } from "@/component/ui/badge";
import { educationAdded, educationUpdated, selectEducation } from "@/store/profile/profileSlice";
import { educationInitialValues, educationSchema } from "@/util/schema";
import { cn } from "@/util/helper";

export function EducationSection() {
    const entries = useSelector(selectEducation);
    const dispatch = useDispatch();
    // null = closed. { entry: null } = adding; { entry } = editing that one.
    const [editing, setEditing] = useState(null);

    function commit(values) {
        dispatch(
            editing.entry
                ? educationUpdated({ id: editing.entry.id, changes: values })
                : educationAdded(values)
        );
        setEditing(null);
    }

    return (
        <Panel>
            <PanelHeader>
                <GraduationCap className="size-[16px] text-primary" />
                <PanelTitle>Education</PanelTitle>
                <Badge variant="soft">{entries.length}</Badge>
                <span className="grow" />
                <button
                    type="button"
                    onClick={() => setEditing({ entry: null })}
                    className="inline-flex items-center gap-1.5 text-[13px] font-medium text-primary hover:underline"
                >
                    <Plus className="size-[14px]" />
                    Add
                </button>
            </PanelHeader>

            <div>
                {entries.length === 0 ? (
                    <p className="px-5 py-6 text-[13.5px] text-muted-foreground">
                        No education yet. Add your degree so tailoring can draw on it.
                    </p>
                ) : (
                    entries.map((entry, i) => (
                        <div
                            key={entry.id}
                            className={cn(
                                "flex flex-wrap items-start gap-4 px-5 py-5",
                                i < entries.length - 1 && "border-b border-border"
                            )}
                        >
                            <span className="grid size-11 shrink-0 place-items-center rounded-md bg-secondary text-muted-foreground">
                                <GraduationCap className="size-[18px]" />
                            </span>
                            <div className="min-w-0 grow">
                                <h3 className="text-[15.5px] font-medium">{entry.degree}</h3>
                                <p className="mt-1 text-[13.5px] text-muted-foreground">
                                    {entry.institution}
                                    {entry.location ? ` · ${entry.location}` : ""}
                                </p>
                                <p className="mt-0.5 text-[12.5px] text-muted-foreground">
                                    {entry.start} — {entry.end}
                                    {entry.note ? ` · ${entry.note}` : ""}
                                </p>
                            </div>
                            <Button
                                variant="ghost"
                                size="sm"
                                className="shrink-0"
                                onClick={() => setEditing({ entry })}
                            >
                                <Pencil />
                                Edit
                            </Button>
                        </div>
                    ))
                )}
            </div>

            {editing ? (
                <Dialog
                    open
                    onClose={() => setEditing(null)}
                    title={editing.entry ? "Edit education" : "Add education"}
                    description="Only the degree and institution are required."
                >
                    <EducationForm
                        entry={editing.entry}
                        onSave={commit}
                        onCancel={() => setEditing(null)}
                    />
                </Dialog>
            ) : null}
        </Panel>
    );
}

function EducationForm({ entry, onSave, onCancel }) {
    const formik = useFormik({
        initialValues: educationInitialValues(entry),
        validationSchema: educationSchema,
        onSubmit: onSave,
    });

    const { touched, errors } = formik;
    const error = (key) => touched[key] && errors[key];

    return (
        <form onSubmit={formik.handleSubmit} noValidate>
            <DialogBody className="flex flex-col gap-5">
                <Field label="Degree" error={error("degree")}>
                    <Input
                        autoFocus
                        placeholder="B.Tech, Computer Science"
                        invalid={Boolean(error("degree"))}
                        {...formik.getFieldProps("degree")}
                    />
                </Field>

                <div className="grid gap-5 sm:grid-cols-2">
                    <Field label="Institution" error={error("institution")}>
                        <Input
                            placeholder="University name"
                            invalid={Boolean(error("institution"))}
                            {...formik.getFieldProps("institution")}
                        />
                    </Field>

                    <Field label="Location">
                        <Input placeholder="City, Country" {...formik.getFieldProps("location")} />
                    </Field>

                    <Field label="Start">
                        <Input placeholder="2014" {...formik.getFieldProps("start")} />
                    </Field>

                    <Field label="End">
                        <Input placeholder="2018" {...formik.getFieldProps("end")} />
                    </Field>
                </div>

                <Field label="Note" hint="Honours, GPA, thesis — anything worth a line.">
                    <Input placeholder="First class with distinction" {...formik.getFieldProps("note")} />
                </Field>
            </DialogBody>

            <DialogFooter>
                <Button type="button" variant="outline" size="sm" onClick={onCancel}>
                    Cancel
                </Button>
                <Button type="submit" size="sm">
                    {entry ? "Save changes" : "Add education"}
                </Button>
            </DialogFooter>
        </form>
    );
}
