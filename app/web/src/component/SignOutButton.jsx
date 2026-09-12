"use client";

import { useRouter } from "next/navigation";
import { useDispatch } from "react-redux";
import { LogOut } from "lucide-react";
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
