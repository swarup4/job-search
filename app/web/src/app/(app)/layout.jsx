"use client";

import { AppShell } from "@/layout/AppShell";

/** Every signed-in screen shares this one header and sidebar; only the page swaps. */
export default function SignedInLayout({ children }) {
    return <AppShell>{children}</AppShell>;
}
