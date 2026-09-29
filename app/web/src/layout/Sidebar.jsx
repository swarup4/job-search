"use client";

import { Suspense } from "react";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { useSelector } from "react-redux";
import {
    Columns3, FileText, ListFilter, Search, Send, Settings2, UserRound, Database, Cpu,
} from "lucide-react";
import { SidebarIdentity } from "@/component/SidebarIdentity";
import { NAV, sectionFor } from "@/routes";
import { selectStatus } from "@/store/status/statusSlice";
import { cn } from "@/util/helper";

const ICON = {
    board: Columns3,
    search: Search,
    shortlist: ListFilter,
    applications: Send,
    profile: UserRound,
    resume: FileText,
    settings: Settings2,
};

export function Sidebar() {
    return (
        <aside className="hidden w-[248px] shrink-0 flex-col gap-5 lg:flex">
            <div className="panel overflow-hidden">
                <SidebarIdentity />

                {/* useSearchParams needs a boundary, or a static page cannot prerender. */}
                <Suspense fallback={<Nav active={null} />}>
                    <RoutedNav />
                </Suspense>
            </div>

            {/* agent health — the template's dot-status idiom, given something real to say */}
            <div className="panel">
                <div className="border-b border-border px-5 py-3.5">
                    <h2 className="text-[13px] font-medium">Agents</h2>
                </div>
                <ul className="px-5 py-3.5">
                    {[
                        { name: "Discovery", note: "ran 4 min ago", ok: true },
                        { name: "Match & score", note: "3 queued", ok: true },
                        { name: "Resume tailor", note: "idle", ok: true },
                        { name: "Tracking", note: "synced", ok: true },
                    ].map((a) => (
                        <li key={a.name} className="flex items-center gap-2.5 py-[7px]">
                            <span
                                className={cn(
                                    "size-2 shrink-0 rounded-full",
                                    a.ok ? "bg-primary" : "bg-muted-foreground"
                                )}
                            />
                            <span className="text-[13px]">{a.name}</span>
                            <span className="grow" />
                            <span className="text-[12px] text-muted-foreground">{a.note}</span>
                        </li>
                    ))}
                </ul>
                <div className="flex items-center gap-2 border-t border-border px-5 py-3">
                    <Cpu className="size-[13px] text-muted-foreground" />
                    <span className="text-[12px] text-muted-foreground">qwen2.5:32b · local</span>
                </div>
            </div>

            <div className="panel">
                <div className="flex items-center gap-2 px-5 py-3.5">
                    <Database className="size-[13px] text-muted-foreground" />
                    <span className="text-[12px] text-muted-foreground">
                        Local Mongo · Atlas vectors
                    </span>
                </div>
            </div>
        </aside>
    );
}

/** A job page highlights the section it was opened from; every other page, its own. */
function RoutedNav() {
    const pathname = usePathname();
    const from = useSearchParams().get("from");
    return <Nav active={activeHref(pathname, from)} />;
}

function activeHref(pathname, from) {
    if (pathname.startsWith("/jobs/")) return sectionFor(from);
    const item = NAV.find(({ href }) =>
        href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`)
    );
    return item?.href ?? null;
}

function Nav({ active }) {
    const { badges } = useSelector(selectStatus);
    return (
        <nav className="p-2">
            {NAV.map((item) => {
                const Icon = ICON[item.icon];
                const isActive = active === item.href;
                const badge = item.badgeKey ? badges[item.badgeKey] : null;
                return (
                    <Link
                        key={item.href}
                        href={item.href}
                        className={cn(
                            "flex items-center gap-3 rounded-md px-3 py-[10px] text-[14px] transition-colors",
                            isActive
                                ? "bg-primary-tint font-medium text-accent-foreground"
                                : "text-muted-foreground hover:bg-secondary hover:text-foreground"
                        )}
                    >
                        <Icon className={cn("size-[17px] shrink-0", isActive && "text-primary")} />
                        <span className="grow">{item.label}</span>
                        {badge ? (
                            <span
                                className={cn(
                                    "grid h-5 min-w-5 place-items-center rounded-pill px-1.5 text-[11px] font-semibold",
                                    item.badgeKey === "pending"
                                        ? "bg-attention-solid text-white"
                                        : "bg-primary text-primary-foreground"
                                )}
                            >
                                {badge}
                            </span>
                        ) : null}
                    </Link>
                );
            })}
        </nav>
    );
}


/**
 * The same links and badges for screens too narrow for the sidebar (below `lg`): one
 * row under the header that scrolls sideways rather than wrapping.
 */
export function MobileNav() {
    return (
        <Suspense fallback={<MobileLinks active={null} />}>
            <RoutedMobileNav />
        </Suspense>
    );
}

function RoutedMobileNav() {
    const pathname = usePathname();
    const from = useSearchParams().get("from");
    return <MobileLinks active={activeHref(pathname, from)} />;
}

function MobileLinks({ active }) {
    const { badges } = useSelector(selectStatus);
    return (
        <nav
            aria-label="Sections"
            className="border-b border-border bg-card lg:hidden"
        >
            <div className="mx-auto flex max-w-[1560px] gap-1.5 overflow-x-auto px-4 py-2 sm:px-6">
                {NAV.map((item) => {
                    const Icon = ICON[item.icon];
                    const isActive = active === item.href;
                    const badge = item.badgeKey ? badges[item.badgeKey] : null;
                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={cn(
                                "flex shrink-0 items-center gap-2 rounded-pill px-3 py-2 text-[13px] whitespace-nowrap transition-colors",
                                isActive
                                    ? "bg-primary-tint font-medium text-accent-foreground"
                                    : "text-muted-foreground hover:bg-secondary hover:text-foreground"
                            )}
                        >
                            <Icon className={cn("size-[15px] shrink-0", isActive && "text-primary")} />
                            {item.label}
                            {badge ? (
                                <span
                                    className={cn(
                                        "grid h-[18px] min-w-[18px] place-items-center rounded-pill px-1 text-[10.5px] font-semibold",
                                        item.badgeKey === "pending"
                                            ? "bg-attention-solid text-white"
                                            : "bg-primary text-primary-foreground"
                                    )}
                                >
                                    {badge}
                                </span>
                            ) : null}
                        </Link>
                    );
                })}
            </div>
        </nav>
    );
}
