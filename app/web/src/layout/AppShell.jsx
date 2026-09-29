"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useSelector } from "react-redux";

import { useRefreshStatus } from "@/hooks/useStatus";
import { ApiError, reportError } from "@/services";
import { MobileNav, Sidebar } from "@/layout/Sidebar";
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
    const refreshStatus = useRefreshStatus();

    useEffect(() => {
        if (status === "anonymous") router.replace(ROUTES.login);
        if (status === "authenticated") refreshStatus();
    }, [status, router, refreshStatus]);

    useEffect(() => {
        if (status !== "authenticated") return;

        const onError = (event) =>
            reportError({
                message: event.message || "Script error",
                detail: event.error?.stack ?? null,
                context: { page: window.location.pathname, at: `${event.filename}:${event.lineno}` },
            });
        const onRejection = (event) => {
            // The axios interceptor already logged these, with the request they came from.
            if (event.reason instanceof ApiError) return;
            reportError({
                message: event.reason?.message ?? String(event.reason),
                detail: event.reason?.stack ?? null,
                context: { page: window.location.pathname },
            });
        };

        window.addEventListener("error", onError);
        window.addEventListener("unhandledrejection", onRejection);
        return () => {
            window.removeEventListener("error", onError);
            window.removeEventListener("unhandledrejection", onRejection);
        };
    }, [status]);

    // "unknown" lasts only until the store reads sessionStorage back, once per refresh.
    if (status !== "authenticated") return null;

    return (
        <div className="min-h-screen bg-background">
            <Topbar />
            <MobileNav />
            <div className="mx-auto flex max-w-[1560px] gap-5 px-4 py-4 sm:px-6 sm:py-6">
                <Sidebar />
                <main className="min-w-0 grow">{children}</main>
            </div>
        </div>
    );
}
