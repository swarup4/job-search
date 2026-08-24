"use client";

import { useState } from "react";
import Link from "next/link";
import { AlertTriangle, UserPlus } from "lucide-react";
import { AuthShell } from "@/component/AuthShell";
import { AuthField } from "@/component/AuthField";
import { Button } from "@/component/ui/button";
import { ROUTES } from "@/routes";

const EMAIL = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
const MIN_PASSWORD = 8;

export default function Page() {
    const [name, setName] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [confirm, setConfirm] = useState("");
    const [message, setMessage] = useState(null);

    const submit = (event) => {
        event.preventDefault();
        if (!name.trim()) return setMessage("Enter your name.");
        if (!email.trim()) return setMessage("Enter your email address.");
        if (!EMAIL.test(email)) return setMessage("That does not look like an email address.");
        if (password.length < MIN_PASSWORD)
            return setMessage(`Use at least ${MIN_PASSWORD} characters for your password.`);
        if (password !== confirm) return setMessage("The two passwords do not match.");
        setMessage("No auth service is connected, so no account can be created yet.");
    };

    return (
        <AuthShell
            title="Create your account"
            subtitle="One profile, one resume, one pipeline."
            footer={
                <>
                    Already set up?{" "}
                    <Link href={ROUTES.login} className="text-primary hover:underline">
                        Sign in
                    </Link>
                </>
            }
        >
            <form onSubmit={submit} noValidate className="mt-6 flex flex-col gap-4">
                <AuthField
                    label="Name"
                    value={name}
                    onChange={setName}
                    placeholder="Your name"
                    autoComplete="name"
                />
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
                    placeholder={`At least ${MIN_PASSWORD} characters`}
                    autoComplete="new-password"
                />
                <AuthField
                    label="Confirm password"
                    type="password"
                    value={confirm}
                    onChange={setConfirm}
                    placeholder="Type it again"
                    autoComplete="new-password"
                />

                {message ? (
                    <p className="flex items-start gap-2 rounded-sm bg-risk px-3 py-2.5 text-[12.5px] leading-relaxed text-pretty text-risk-ink">
                        <AlertTriangle className="mt-0.5 size-[13px] shrink-0" />
                        {message}
                    </p>
                ) : null}

                <Button type="submit" className="mt-1 w-full">
                    <UserPlus />
                    Create account
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
