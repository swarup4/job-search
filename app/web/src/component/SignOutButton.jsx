"use client";

import { useRouter } from "next/navigation";
import { LogOut } from "lucide-react";
import { clearSession } from "@/lib/session";
import { ROUTES } from "@/routes";

export function SignOutButton() {
    const router = useRouter();

    function signOut() {
        clearSession();
        router.replace(ROUTES.login);
    }

    return (
        <button
            type="button"
            onClick={signOut}
            title="Sign out"
            aria-label="Sign out"
            className="grid size-10 place-items-center rounded-pill hover:bg-secondary"
        >
            <LogOut className="size-[17px] text-muted-foreground" />
        </button>
    );
}
