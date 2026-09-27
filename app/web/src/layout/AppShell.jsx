"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useSelector } from "react-redux";

import { useRefreshShell } from "@/hooks/useShellCounts";
import { Sidebar } from "@/layout/Sidebar";
import { Topbar } from "@/layout/Topbar";
import { ROUTES } from "@/routes";
import { selectAuthStatus } from "@/store/auth/authSlice";

/**
 * The header and sidebar, rendered once by `app/(app)/layout.jsx` and kept mounted
 * while pages change beneath them. Pages render only their own content.
 */
export function AppShell({ children }) {
    const router = useRouter();
    const status = useSelector(selectAuthStatus);
    const refreshShell = useRefreshShell();

    useEffect(() => {
        if (status === "anonymous") router.replace(ROUTES.login);
        if (status === "authenticated") refreshShell();
    }, [status, router, refreshShell]);

    // "unknown" lasts only until the store reads sessionStorage back, once per refresh.
    if (status !== "authenticated") return null;

    return (
        <div className="min-h-screen bg-background">
            <Topbar />
            <div className="mx-auto flex max-w-[1560px] gap-5 px-6 py-6">
                <Sidebar />
                <main className="min-w-0 grow">{children}</main>
            </div>
        </div>
    );
}
