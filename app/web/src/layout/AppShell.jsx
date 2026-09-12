"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useSelector } from "react-redux";

import { Sidebar } from "@/layout/Sidebar";
import { Topbar } from "@/layout/Topbar";
import { ROUTES } from "@/routes";
import { selectAuthStatus } from "@/store/auth/authSlice";

export function AppShell({ active, children, counts = {}, aside = true }) {
    const router = useRouter();
    const status = useSelector(selectAuthStatus);

    useEffect(() => {
        if (status === "anonymous") router.replace(ROUTES.login);
    }, [status, router]);

    // "unknown" lasts only until the store reads sessionStorage back, once per refresh.
    // Every later navigation already knows the answer, so nothing blanks in between —
    // which is what used to make each page change flicker.
    if (status !== "authenticated") return null;

    return (
        <div className="min-h-screen bg-background">
            <Topbar pending={counts.pending ?? 0} />
            <div className="mx-auto flex max-w-[1560px] gap-5 px-6 py-6">
                {aside ? <Sidebar active={active} counts={counts} /> : null}
                <main className="min-w-0 grow">{children}</main>
            </div>
        </div>
    );
}
