"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useFormik } from "formik";
import { AlertTriangle, Eye, EyeOff, Loader2, LogIn } from "lucide-react";
import { AuthShell } from "@/component/AuthShell";
import { Field, Input } from "@/component/ui/field";
import { Button } from "@/component/ui/button";
import { loginInitialValues, loginSchema } from "@/util/schema";
import { login } from "@/services/auth";
import { ApiError } from "@/services";
import { ROUTES } from "@/routes";

export default function Page() {
    const [revealed, setRevealed] = useState(false);
    const router = useRouter();

    const formik = useFormik({
        initialValues: loginInitialValues,
        validationSchema: loginSchema,
        onSubmit: async (values, { setStatus }) => {
            setStatus(null);
            try {
                await login(values);
                // Back to whatever the guard interrupted, or the dashboard. Read here
                // rather than with useSearchParams, which needs a Suspense boundary.
                const next = new URLSearchParams(window.location.search).get("next");
                router.replace(next || ROUTES.board);
            } catch (error) {
                setStatus(
                    error instanceof ApiError ? error.message : "Could not sign you in."
                );
            }
        },
    });

    const { touched, errors } = formik;
    const emailError = touched.email && errors.email;
    const passwordError = touched.password && errors.password;

    return (
        <AuthShell
            title="Sign in"
            subtitle="Pick up where you left off in your pipeline."
            footer={
                <>
                    No account?{" "}
                    <Link href={ROUTES.signup} className="text-primary hover:underline">
                        Create one
                    </Link>
                </>
            }
        >
            <form onSubmit={formik.handleSubmit} noValidate className="mt-6 flex flex-col gap-4">
                <Field label="Email" error={emailError}>
                    <Input
                        type="email"
                        placeholder="you@example.com"
                        autoComplete="username"
                        invalid={Boolean(emailError)}
                        {...formik.getFieldProps("email")}
                    />
                </Field>

                <Field label="Password" error={passwordError}>
                    <span className="relative block">
                        <Input
                            type={revealed ? "text" : "password"}
                            placeholder="••••••••"
                            autoComplete="current-password"
                            className="pr-11"
                            invalid={Boolean(passwordError)}
                            {...formik.getFieldProps("password")}
                        />
                        <button
                            type="button"
                            onClick={() => setRevealed((r) => !r)}
                            aria-label={revealed ? "Hide password" : "Show password"}
                            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                        >
                            {revealed ? (
                                <EyeOff className="size-[15px]" />
                            ) : (
                                <Eye className="size-[15px]" />
                            )}
                        </button>
                    </span>
                </Field>

                {formik.status ? (
                    <p className="flex items-start gap-2 rounded-sm bg-risk px-3 py-2.5 text-[12.5px] leading-relaxed text-pretty text-risk-ink">
                        <AlertTriangle className="mt-0.5 size-[13px] shrink-0" />
                        {formik.status}
                    </p>
                ) : null}

                <Button type="submit" disabled={formik.isSubmitting} className="mt-1 w-full">
                    {formik.isSubmitting ? <Loader2 className="animate-spin" /> : <LogIn />}
                    {formik.isSubmitting ? "Signing in" : "Sign in"}
                </Button>
            </form>
        </AuthShell>
    );
}
