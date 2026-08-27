"use client";

import { useFormik } from "formik";
import { useRouter } from "next/navigation";
import { AlertTriangle, Loader2, UserPlus } from "lucide-react";
import { ApiError, createProfile } from "@/services";
import { Panel, PanelBody } from "@/component/ui/panel";
import { Field, Input } from "@/component/ui/field";
import { Button } from "@/component/ui/button";
import { profileCreateInitialValues, profileCreateSchema } from "@/util/schema";

/**
 * Shown when the API has no profile yet. Creation is explicit rather than
 * auto-seeded: `email` is mandatory, so there is no blank profile to conjure.
 */
export function EmptyProfile() {
    const router = useRouter();

    const formik = useFormik({
        initialValues: profileCreateInitialValues,
        validationSchema: profileCreateSchema,
        onSubmit: async (values, { setStatus, setSubmitting }) => {
            setStatus(null);
            try {
                await createProfile({
                    email: values.email,
                    personal: { name: values.name },
                });
                router.refresh();
            } catch (error) {
                // The server validates independently; surface its message rather than
                // guessing which field it objected to.
                setStatus(
                    error instanceof ApiError ? error.message : "Could not create the profile."
                );
                setSubmitting(false);
            }
        },
    });

    const { touched, errors } = formik;
    const nameError = touched.name && errors.name;
    const emailError = touched.email && errors.email;

    return (
        <Panel className="mx-auto max-w-[520px]">
            <PanelBody className="py-8">
                <div>
                    <h1 className="text-[20px] font-medium">Set up your details</h1>
                    <p className="mt-2 text-[14px] leading-relaxed text-pretty text-muted-foreground">
                        Nothing can be scored or tailored until this exists — the no-fabrication rule
                        works by only ever drawing on what you put here.
                    </p>
                </div>

                <form onSubmit={formik.handleSubmit} noValidate className="mt-5 flex flex-col gap-5">
                    <Field label="Full name" error={nameError}>
                        <Input
                            placeholder="Your name"
                            invalid={Boolean(nameError)}
                            {...formik.getFieldProps("name")}
                        />
                    </Field>

                    <Field
                        label="Email"
                        hint="Required — this is your profile's key."
                        error={emailError}
                    >
                        <Input
                            type="email"
                            placeholder="you@example.com"
                            invalid={Boolean(emailError)}
                            {...formik.getFieldProps("email")}
                        />
                    </Field>

                    {formik.status ? (
                        <p className="flex items-start gap-2 rounded-sm bg-risk px-3 py-2.5 text-[12.5px] leading-relaxed text-pretty text-risk-ink">
                            <AlertTriangle className="mt-0.5 size-[13px] shrink-0" />
                            {formik.status}
                        </p>
                    ) : null}

                    <Button type="submit" disabled={formik.isSubmitting} className="w-full">
                        {formik.isSubmitting ? (
                            <Loader2 className="animate-spin" />
                        ) : (
                            <UserPlus />
                        )}
                        Create profile
                    </Button>
                </form>
            </PanelBody>
        </Panel>
    );
}
