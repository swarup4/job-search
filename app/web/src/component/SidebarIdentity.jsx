"use client";

import { useSelector } from "react-redux";

import { selectUser } from "@/store/auth/authSlice";
import { initials } from "@/util/helper";

/** Who is signed in, at the top of the sidebar. Read from the store, so a refresh
 * and a navigation both show the same thing without touching storage here. */
export function SidebarIdentity() {
    const user = useSelector(selectUser);

    return (
        <div className="flex items-center gap-3 border-b border-border px-5 py-4">
            <span className="grid size-10 shrink-0 place-items-center rounded-md bg-primary-tint text-[13px] font-semibold text-primary">
                {initials(user?.name)}
            </span>
            <div className="min-w-0">
                <p className="truncate text-[15px] font-semibold leading-tight">{user?.name}</p>
                <p className="truncate text-[12px] text-muted-foreground">
                    {user?.role || user?.email}
                </p>
            </div>
        </div>
    );
}
