"use client";

import { useRouter } from "next/navigation";
import { useDispatch } from "react-redux";
import { LogOut } from "lucide-react";
import { Tooltip } from "@/component/ui/tooltip";
import { signedOut } from "@/store/auth/authSlice";
import { ROUTES } from "@/routes";

export function SignOutButton() {
    const router = useRouter();
    const dispatch = useDispatch();

    function signOut() {
        dispatch(signedOut());
        router.replace(ROUTES.login);
    }

    return (
        // Below, not above: the button sits at the top of the page.
        <Tooltip content="Sign out" align="end" side="bottom" className="shrink-0">
            <button
                type="button"
                onClick={signOut}
                aria-label="Sign out"
                className="grid size-10 place-items-center rounded-pill hover:bg-secondary"
            >
                <LogOut className="size-[17px] text-muted-foreground" />
            </button>
        </Tooltip>
    );
}
