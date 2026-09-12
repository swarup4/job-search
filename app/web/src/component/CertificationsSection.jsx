"use client";

import { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useFormik } from "formik";
import { Award, Pencil, Plus } from "lucide-react";
import { Panel, PanelHeader, PanelTitle } from "@/component/ui/panel";
import { Dialog, DialogBody, DialogFooter } from "@/component/ui/dialog";
import { Field, Input } from "@/component/ui/field";
import { Button } from "@/component/ui/button";
import { Badge } from "@/component/ui/badge";
import {
    certificationAdded,
    certificationUpdated,
    selectCertifications,
} from "@/store/profile/profileSlice";
import { certificationInitialValues, certificationSchema } from "@/util/schema";
import { cn } from "@/util/helper";

export function CertificationsSection() {
    const entries = useSelector(selectCertifications);
    const dispatch = useDispatch();
    // null = closed. { entry: null } = adding; { entry } = editing that one.
    const [editing, setEditing] = useState(null);

    function commit(values) {
        dispatch(
            editing.entry
                ? certificationUpdated({ id: editing.entry.id, changes: values })
                : certificationAdded(values)
        );
        setEditing(null);
    }

    const lastLineStart = entries.length - (entries.length % 2 === 0 ? 2 : 1);

    return (
        <Panel>
            <PanelHeader>
                <Award className="size-[16px] text-primary" />
                <PanelTitle>Certifications</PanelTitle>
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

            {entries.length === 0 ? (
                <p className="px-5 py-6 text-[13.5px] text-muted-foreground">
                    No certifications yet.
                </p>
            ) : (
                <div className="grid sm:grid-cols-2">
                    {entries.map((cert, i) => (
                        <div
                            key={cert.id}
                            className={cn(
                                "flex items-start gap-3 px-5 py-4",
                                i < lastLineStart && "border-b border-border",
                                i % 2 === 0 && "sm:border-r sm:border-border"
                            )}
                        >
                            <Award className="mt-0.5 size-[15px] shrink-0 text-muted-foreground" />
                            <div className="min-w-0 grow">
                                <p className="text-[13.5px] font-medium leading-snug">{cert.name}</p>
                                <p className="mt-1 text-[12.5px] text-muted-foreground">
                                    {cert.issuer}
                                    {cert.year ? ` · ${cert.year}` : ""}
                                </p>
                            </div>
                            <button
                                type="button"
                                aria-label={`Edit ${cert.name}`}
                                onClick={() => setEditing({ entry: cert })}
                                className="grid size-8 shrink-0 place-items-center rounded-sm text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
                            >
                                <Pencil className="size-[14px]" />
                            </button>
                        </div>
                    ))}
                </div>
            )}

            {editing ? (
                <Dialog
                    open
                    onClose={() => setEditing(null)}
                    title={editing.entry ? "Edit certification" : "Add certification"}
                    description="Name and issuer are required."
                >
                    <CertificationForm
                        entry={editing.entry}
                        onSave={commit}
                        onCancel={() => setEditing(null)}
                    />
                </Dialog>
            ) : null}
        </Panel>
    );
}

function CertificationForm({ entry, onSave, onCancel }) {
    const formik = useFormik({
        initialValues: certificationInitialValues(entry),
        validationSchema: certificationSchema,
        onSubmit: onSave,
    });

    const { touched, errors } = formik;
    const error = (key) => touched[key] && errors[key];

    return (
        <form onSubmit={formik.handleSubmit} noValidate>
            <DialogBody className="flex flex-col gap-5">
                <Field label="Certification" error={error("name")}>
                    <Input
                        autoFocus
                        placeholder="MongoDB Associate Developer"
                        invalid={Boolean(error("name"))}
                        {...formik.getFieldProps("name")}
                    />
                </Field>

                <div className="grid gap-5 sm:grid-cols-2">
                    <Field label="Issuer" error={error("issuer")}>
                        <Input
                            placeholder="MongoDB"
                            invalid={Boolean(error("issuer"))}
                            {...formik.getFieldProps("issuer")}
                        />
                    </Field>

                    <Field label="Year" error={error("year")}>
                        <Input
                            placeholder="2024"
                            inputMode="numeric"
                            invalid={Boolean(error("year"))}
                            {...formik.getFieldProps("year")}
                        />
                    </Field>
                </div>
            </DialogBody>

            <DialogFooter>
                <Button type="button" variant="outline" size="sm" onClick={onCancel}>
                    Cancel
                </Button>
                <Button type="submit" size="sm">
                    {entry ? "Save changes" : "Add certification"}
                </Button>
            </DialogFooter>
        </form>
    );
}
