"use client";

import { useState } from "react";
import { useDispatch, useSelector, useStore } from "react-redux";
import { useFormik } from "formik";
import { Pencil, Plus, X } from "lucide-react";
// MOCK: saving is stubbed while the endpoint is being built.
// import { updateProfile } from "@/services";
import { ApiError } from "@/services";
import { Panel, PanelBody, PanelHeader, PanelTitle } from "@/component/ui/panel";
import { Field, Input, Textarea } from "@/component/ui/field";
import { Button } from "@/component/ui/button";
import { ProfileSaveBar } from "@/component/ProfileSaveBar";
import {
    identityChanged,
    linkAdded,
    linkChanged,
    linkRemoved,
    profileSaved,
    selectIdentity,
    selectProfilePayload,
} from "@/store/profile/profileSlice";
import { useDebounce } from "@/hooks/useDebounce";
import { profileIdentitySchema } from "@/util/schema";
import { initials } from "@/util/helper";

export function ProfileIdentity() {
    const identity = useSelector(selectIdentity);
    const store = useStore();
    const dispatch = useDispatch();
    const { schedule, flush } = useDebounce();

    const formik = useFormik({
        initialValues: identity,
        validationSchema: profileIdentitySchema,
        onSubmit: async (values, { setStatus }) => {
            debugger;
            setStatus(null);
            // Anything still waiting on the debounce belongs in this save.
            flush();
            // The payload is the whole profile, not just this form — every section
            // has been writing to the store as it was edited.
            const payload = selectProfilePayload(store.getState());
            try {
                // await updateProfile(payload);
                await new Promise((resolve) => setTimeout(resolve, 400));
                dispatch(profileSaved());
                setStatus({ ok: true, message: "Saved (mock — not persisted)." });
            } catch (error) {
                setStatus({
                    ok: false,
                    message: error instanceof ApiError ? error.message : "Could not save.",
                });
            }
        },
    });

    const { values, touched, errors, status, isSubmitting } = formik;

    const bind = (field) => ({
        ...formik.getFieldProps(field),
        onChange: (e) => {
            formik.handleChange(e);
            const { value } = e.target;
            schedule(field, () => dispatch(identityChanged({ field, value })));
        },
    });
    const error = (key) => touched[key] && errors[key];

    // Structural link edits reach the store at once; only the typed value waits.
    function addLink(label) {
        flush();
        dispatch(linkAdded(label));
        formik.setFieldValue("links", [...values.links, { label, value: "" }]);
    }

    function removeLink(index) {
        flush();
        dispatch(linkRemoved(index));
        formik.setFieldValue(
            "links",
            values.links.filter((_, i) => i !== index)
        );
    }

    return (
        <form onSubmit={formik.handleSubmit} noValidate className="flex flex-col gap-5">
            <ProfileSaveBar status={status} isSubmitting={isSubmitting} />

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
                        <Field label="Full name" error={error("name")}>
                            <Input invalid={Boolean(error("name"))} {...bind("name")} />
                        </Field>

                        <Field
                            label="Headline"
                            hint="Context for scoring. Never written into the resume."
                        >
                            <Input {...bind("headline")} />
                        </Field>

                        <Field
                            label="Email"
                            hint="Required — this is your profile's key."
                            error={error("email")}
                        >
                            <Input
                                type="email"
                                invalid={Boolean(error("email"))}
                                {...bind("email")}
                            />
                        </Field>

                        <Field label="Phone">
                            <Input {...bind("phone")} />
                        </Field>

                        <Field label="Location" className="sm:col-span-2">
                            <Input {...bind("location")} />
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
                                    <Field className="min-w-[240px] grow">
                                        <Input
                                            {...formik.getFieldProps(`links.${i}.value`)}
                                            onChange={(e) => {
                                                formik.handleChange(e);
                                                const { value } = e.target;
                                                schedule(`links.${i}`, () =>
                                                    dispatch(
                                                        linkChanged({ index: i, value })
                                                    )
                                                );
                                            }}
                                        />
                                    </Field>
                                    <button
                                        type="button"
                                        aria-label={`Remove ${link.label}`}
                                        onClick={() => removeLink(i)}
                                        className="grid size-9 shrink-0 place-items-center rounded-sm text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
                                    >
                                        <X className="size-[14px]" />
                                    </button>
                                </div>
                            ))}
                            <AddLink
                                taken={values.links.map((l) => l.label)}
                                onAdd={addLink}
                            />
                        </div>
                    </div>
                </PanelBody>
            </Panel>

            <Panel>
                <PanelHeader>
                    <PanelTitle>Professional summary</PanelTitle>
                </PanelHeader>
                <PanelBody className="py-5">
                    <Textarea className="min-h-[124px]" {...bind("summary")} />
                </PanelBody>
            </Panel>
        </form>
    );
}

/** Labels are the key the rows render by, so a new one may not collide. */
function AddLink({ taken, onAdd }) {
    const [label, setLabel] = useState(null);

    function commit() {
        const next = (label ?? "").trim();
        if (next && !taken.includes(next)) onAdd(next);
        setLabel(null);
    }

    if (label === null) {
        return (
            <button
                type="button"
                onClick={() => setLabel("")}
                className="inline-flex w-fit items-center gap-1.5 text-[13px] font-medium text-primary hover:underline"
            >
                <Plus className="size-[14px]" />
                Add link
            </button>
        );
    }

    return (
        <Input
            autoFocus
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            onBlur={commit}
            onKeyDown={(e) => {
                if (e.key === "Enter") {
                    e.preventDefault();
                    commit();
                } else if (e.key === "Escape") {
                    setLabel(null);
                }
            }}
            placeholder="Link label — LinkedIn, GitHub, Portfolio…"
            className="w-fit min-w-[280px]"
        />
    );
}
