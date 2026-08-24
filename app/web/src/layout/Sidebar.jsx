import Link from "next/link";
import {
    Columns3, ListFilter, Search, Send, Settings2, Sparkles, UserRound, Database, Cpu,
} from "lucide-react";
import { NAV } from "@/routes";
import { cn } from "@/util/cn";

const ICON = {
    board: Columns3,
    search: Search,
    shortlist: ListFilter,
    applications: Send,
    profile: UserRound,
    settings: Settings2,
};

export function Sidebar({ active, counts = {} }) {
    return (
        <aside className="hidden w-[248px] shrink-0 flex-col gap-5 lg:flex">
            <div className="panel overflow-hidden">
                <div className="flex items-center gap-3 border-b border-border px-5 py-4">
                    <span className="grid size-10 shrink-0 place-items-center rounded-md bg-primary-tint text-primary">
                        <Sparkles className="size-[18px]" />
                    </span>
                    <div className="min-w-0">
                        <p className="truncate text-[15px] font-semibold leading-tight">Swarup Saha</p>
                        <p className="truncate text-[12px] text-muted-foreground">Technical Lead · GenAI</p>
                    </div>
                </div>

                <nav className="p-2">
                    {NAV.map((item) => {
                        const Icon = ICON[item.icon];
                        const isActive = active === item.href;
                        const badge = item.badgeKey ? counts[item.badgeKey] : null;
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
