"use client";

import { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useFormik } from "formik";
import { AlertTriangle, Award, Pencil, Plus } from "lucide-react";
import { Panel, PanelHeader, PanelTitle } from "@/component/ui/panel";
import { Dialog, DialogBody, DialogFooter } from "@/component/ui/dialog";
import { Field, Input, Select } from "@/component/ui/field";
import { Button } from "@/component/ui/button";
import { Badge } from "@/component/ui/badge";
import { ApiError, addCertification, updateCertification } from "@/services";
import {
    certificationAdded,
    certificationUpdated,
    selectCertifications,
} from "@/store/profile/profileSlice";
import { certificationInitialValues, certificationSchema } from "@/util/schema";
import { MONTHS, joinMonthYear } from "@/util/helper";
import { cn } from "@/util/helper";

export function CertificationsSection() {
    const entries = useSelector(selectCertifications);
    const dispatch = useDispatch();
    // null = closed. { entry: null } = adding; { entry } = editing that one.
    const [editing, setEditing] = useState(null);

    // Writes straight through — this dialog's Save is the only save there is.
    async function commit(values) {
        const { entry } = editing;
        // Month and year are two fields on the form and one string in the document.
        const body = {
            name: values.name,
            issuer: values.issuer,
            year: joinMonthYear(values.month, values.year),
        };
        const saved = entry
            ? await updateCertification(entry.id, body)
            : await addCertification(body);
        dispatch(
            entry ? certificationUpdated({ id: saved.id, changes: saved }) : certificationAdded(saved)
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
        onSubmit: async (values, { setStatus, setSubmitting }) => {
            setStatus(null);
            try {
                await onSave(values);
            } catch (error) {
                setStatus(error instanceof ApiError ? error.message : "Could not save.");
                setSubmitting(false);
            }
        },
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

                    <Field label="Earned" error={error("year")}>
                        <div className="flex gap-2.5">
                            <Select className="w-[104px]" {...formik.getFieldProps("month")}>
                                <option value="">Month</option>
                                {MONTHS.map((m) => (
                                    <option key={m} value={m}>{m}</option>
                                ))}
                            </Select>
                            <Input
                                placeholder="2024"
                                inputMode="numeric"
                                invalid={Boolean(error("year"))}
                                {...formik.getFieldProps("year")}
                            />
                        </div>
                    </Field>
                </div>

                {formik.status ? (
                    <p className="flex items-start gap-2 rounded-sm bg-risk px-3 py-2.5 text-[12.5px] leading-relaxed text-risk-ink">
                        <AlertTriangle className="mt-0.5 size-[13px] shrink-0" />
                        {formik.status}
                    </p>
                ) : null}
            </DialogBody>

            <DialogFooter>
                <Button type="button" variant="outline" size="sm" onClick={onCancel}>
                    Cancel
                </Button>
                <Button type="submit" size="sm" disabled={formik.isSubmitting}>
                    {entry ? "Save changes" : "Add certification"}
                </Button>
            </DialogFooter>
        </form>
    );
}
