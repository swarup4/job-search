"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useDispatch, useSelector } from "react-redux";

import { Sidebar } from "@/layout/Sidebar";
import { Topbar } from "@/layout/Topbar";
import { readToken } from "@/lib/session";
import { ROUTES } from "@/routes";
import { countsSet, selectCounts } from "@/store/shell/shellSlice";

export function AppShell({ active, children, counts = {}, aside = true }) {
    const dispatch = useDispatch();
    const router = useRouter();
    const seeded = useRef(false);

    // Before the selector below, so the first paint already has the real numbers.
    if (!seeded.current) {
        seeded.current = true;
        dispatch(countsSet(counts));
    }

    const live = useSelector(selectCounts);

    // Every signed-in page renders through here, so this is the whole route guard.
    // sessionStorage only exists on the client, hence the wait before painting.
    const [allowed, setAllowed] = useState(false);
    useEffect(() => {
        if (readToken()) setAllowed(true);
        else router.replace(ROUTES.login);
    }, [router]);

    if (!allowed) return null;

    return (
        <div className="min-h-screen bg-background">
            <Topbar pending={live.pending} />
            <div className="mx-auto flex max-w-[1560px] gap-5 px-6 py-6">
                {aside ? <Sidebar active={active} counts={live} /> : null}
                <main className="min-w-0 grow">{children}</main>
            </div>
        </div>
    );
}
