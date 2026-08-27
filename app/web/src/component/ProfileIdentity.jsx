"use client";

import { useFormik, getIn } from "formik";
import { AlertTriangle, Check, Loader2, Pencil, Plus, Save } from "lucide-react";
import { ApiError, updateProfile } from "@/services";
import { Panel, PanelBody, PanelHeader, PanelTitle } from "@/component/ui/panel";
import { Field, Input, Textarea } from "@/component/ui/field";
import { Button } from "@/component/ui/button";
import { profileIdentityInitialValues, profileIdentitySchema } from "@/util/schema";

/**
 * The editable half of My details. Client-side because it saves; the read-only
 * sections below it on the page stay server-rendered.
 *
 * `email` is mandatory and is the profile's key — Yup catches a blank or malformed
 * one before the request, and the server's own 422 still surfaces here if it
 * objects to something the schema does not know about.
 */
export function ProfileIdentity({ profile }) {
    const formik = useFormik({
        initialValues: profileIdentityInitialValues(profile),
        validationSchema: profileIdentitySchema,
        onSubmit: async (values, { setStatus, resetForm }) => {
            setStatus(null);
            try {
                await updateProfile({
                    email: values.email,
                    personal: {
                        name: values.name,
                        headline: values.headline || null,
                        phone: values.phone || null,
                        location: values.location || null,
                        links: values.links,
                    },
                    summary: values.summary || null,
                });
                setStatus({ ok: true, message: "Saved." });
                // New clean baseline, so the confirmation hides itself the moment you
                // start editing again instead of claiming stale changes are saved.
                resetForm({ values });
            } catch (error) {
                setStatus({
                    ok: false,
                    message: error instanceof ApiError ? error.message : "Could not save.",
                });
            }
        },
    });

    const { values, touched, errors, status, dirty, isSubmitting } = formik;
    const nameError = touched.name && errors.name;
    const emailError = touched.email && errors.email;

    return (
        <form onSubmit={formik.handleSubmit} noValidate>
            <div className="mb-5 flex flex-wrap items-center gap-3">
                <span className="grow" />
                {status && (!status.ok || !dirty) ? <Notice status={status} /> : null}
                <Button type="submit" size="sm" disabled={isSubmitting}>
                    {isSubmitting ? <Loader2 className="animate-spin" /> : <Save />}
                    {isSubmitting ? "Saving" : "Save changes"}
                </Button>
            </div>

            <div className="flex flex-col gap-5">
                <Panel>
                    <PanelHeader>
                        <PanelTitle>Personal details</PanelTitle>
                    </PanelHeader>
                    <PanelBody className="flex flex-col gap-5 py-5">
                        <div className="flex flex-wrap items-center gap-4">
                            <span className="grid size-16 shrink-0 place-items-center rounded-full bg-primary-tint text-[20px] font-semibold text-primary">
                                {initials(values.name)}
                            </span>
                            <div className="min-w-0">
                                <p className="text-[18px] font-semibold">
                                    {values.name || "Unnamed"}
                                </p>
                                <p className="mt-0.5 text-[13.5px] text-muted-foreground">
                                    {values.headline || "No headline"}
                                </p>
                            </div>
                            <span className="grow" />
                            <Button type="button" variant="outline" size="sm">
                                <Pencil />
                                Replace photo
                            </Button>
                        </div>

                        <div className="grid gap-5 sm:grid-cols-2">
                            <Field label="Full name" error={nameError}>
                                <Input
                                    invalid={Boolean(nameError)}
                                    {...formik.getFieldProps("name")}
                                />
                            </Field>

                            <Field
                                label="Headline"
                                hint="Context for scoring. Never written into the resume."
                            >
                                <Input {...formik.getFieldProps("headline")} />
                            </Field>

                            <Field
                                label="Email"
                                hint="Required — this is your profile's key."
                                error={emailError}
                            >
                                <Input
                                    type="email"
                                    invalid={Boolean(emailError)}
                                    {...formik.getFieldProps("email")}
                                />
                            </Field>

                            <Field label="Phone">
                                <Input {...formik.getFieldProps("phone")} />
                            </Field>

                            <Field label="Location" className="sm:col-span-2">
                                <Input {...formik.getFieldProps("location")} />
                            </Field>
                        </div>

                        <div>
                            <p className="mb-2.5 text-[13px] font-medium">Links</p>
                            <div className="flex flex-col gap-3">
                                {values.links.map((link, i) => (
                                    <div
                                        key={link.label}
                                        className="flex flex-wrap items-center gap-3"
                                    >
                                        <span className="w-20 shrink-0 text-[13px] text-muted-foreground">
                                            {link.label}
                                        </span>
                                        {/* getIn, not errors[name]: Formik shapes errors like
                                            values, so `links.0.value` is a path, not a key. */}
                                        <Field
                                            className="min-w-[240px] grow"
                                            error={getIn(errors, `links.${i}.value`)}
                                        >
                                            <Input
                                                {...formik.getFieldProps(`links.${i}.value`)}
                                            />
                                        </Field>
                                    </div>
                                ))}
                                <button
                                    type="button"
                                    className="inline-flex w-fit items-center gap-1.5 text-[13px] font-medium text-primary hover:underline"
                                >
                                    <Plus className="size-[14px]" />
                                    Add link
                                </button>
                            </div>
                        </div>
                    </PanelBody>
                </Panel>

                <Panel>
                    <PanelHeader>
                        <PanelTitle>Professional summary</PanelTitle>
                    </PanelHeader>
                    <PanelBody className="py-5">
                        <Textarea
                            className="min-h-[124px]"
                            {...formik.getFieldProps("summary")}
                        />
                    </PanelBody>
                </Panel>
            </div>
        </form>
    );
}

function Notice({ status }) {
    return (
        <p
            className={
                status.ok
                    ? "flex items-center gap-2 rounded-sm bg-primary-tint px-3 py-2 text-[12.5px] text-accent-foreground"
                    : "flex items-start gap-2 rounded-sm bg-risk px-3 py-2 text-[12.5px] text-risk-ink"
            }
        >
            {status.ok ? (
                <Check className="size-[13px] shrink-0" />
            ) : (
                <AlertTriangle className="mt-0.5 size-[13px] shrink-0" />
            )}
            {status.message}
        </p>
    );
}

function initials(name) {
    return name.split(" ").filter(Boolean).map((p) => p[0]).join("") || "?";
}
