"use client";

import { useState } from "react";
import Link from "next/link";
import { AlertTriangle, LogIn } from "lucide-react";
import { AuthShell } from "@/component/AuthShell";
import { AuthField } from "@/component/AuthField";
import { Button } from "@/component/ui/button";
import { ROUTES } from "@/routes";

const EMAIL = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

export default function Page() {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [message, setMessage] = useState(null);

    const submit = (event) => {
        event.preventDefault();
        if (!email.trim()) return setMessage("Enter your email address.");
        if (!EMAIL.test(email)) return setMessage("That does not look like an email address.");
        if (!password) return setMessage("Enter your password.");
        setMessage("No auth service is connected, so there is nothing to sign in to yet.");
    };

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
            <form onSubmit={submit} noValidate className="mt-6 flex flex-col gap-4">
                <AuthField
                    label="Email"
                    type="email"
                    value={email}
                    onChange={setEmail}
                    placeholder="you@example.com"
                    autoComplete="username"
                />
                <AuthField
                    label="Password"
                    type="password"
                    value={password}
                    onChange={setPassword}
                    placeholder="••••••••"
                    autoComplete="current-password"
                />

                {message ? <Notice text={message} /> : null}

                <Button type="submit" className="mt-1 w-full">
                    <LogIn />
                    Sign in
                </Button>

                <Link
                    href={ROUTES.board}
                    className="text-center text-[13px] text-muted-foreground hover:text-primary"
                >
                    Skip — go straight to the dashboard
                </Link>
            </form>
        </AuthShell>
    );
}

function Notice({ text }) {
    return (
        <p className="flex items-start gap-2 rounded-sm bg-risk px-3 py-2.5 text-[12.5px] leading-relaxed text-pretty text-risk-ink">
            <AlertTriangle className="mt-0.5 size-[13px] shrink-0" />
            {text}
        </p>
    );
}
