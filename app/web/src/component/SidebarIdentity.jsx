"use client";

import { readSession } from "@/lib/session";
import { initials } from "@/util/helper";

/**
 * Who is signed in, at the top of the sidebar. Read during render rather than in an
 * effect: AppShell renders nothing until the guard passes, so this never runs on the
 * server and there is no mismatch to hydrate.
 */
export function SidebarIdentity() {
    const user = readSession()?.user;

    return (
        <div className="flex items-center gap-3 border-b border-border px-5 py-4">
            <span className="grid size-10 shrink-0 place-items-center rounded-md bg-primary-tint text-[13px] font-semibold text-primary">
                {initials(user?.name)}
            </span>
            <div className="min-w-0">
                <p className="truncate text-[15px] font-semibold leading-tight">{user?.name}</p>
                <p className="truncate text-[12px] text-muted-foreground">{user?.email}</p>
            </div>
        </div>
    );
}
