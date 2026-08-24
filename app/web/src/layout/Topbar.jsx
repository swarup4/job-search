import Link from "next/link";
import { Bell, RefreshCw, Search } from "lucide-react";
import { Button } from "@/component/ui/button";
import { ROUTES } from "@/routes";

export function Topbar({ pending = 0 }) {
    return (
        <header className="sticky top-0 z-20 border-b border-border bg-card">
            <div className="mx-auto flex h-[68px] max-w-[1560px] items-center gap-5 px-6">
                <Link href={ROUTES.board} className="flex items-center gap-2.5">
                    <Mark />
                    <span className="text-[20px] font-bold tracking-tight">
                        Job<span className="text-primary">Pilot</span>
                    </span>
                </Link>

                <div className="ml-4 hidden max-w-[420px] grow items-center gap-2.5 rounded-pill bg-secondary px-4 py-2.5 md:flex">
                    <Search className="size-[15px] shrink-0 text-muted-foreground" />
                    <input
                        placeholder="Search roles, companies, keywords"
                        className="w-full bg-transparent text-[14px] outline-none placeholder:text-muted-foreground"
                    />
                </div>

                <div className="grow" />

                <span className="hidden text-[13px] text-muted-foreground lg:inline">
                    Synced 4 min ago
                </span>

                <button className="relative grid size-10 place-items-center rounded-pill hover:bg-secondary">
                    <Bell className="size-[17px] text-muted-foreground" />
                    {pending > 0 ? (
                        <span className="absolute right-1.5 top-1.5 grid size-[17px] place-items-center rounded-full bg-attention-solid text-[10px] font-bold text-white">
                            {pending}
                        </span>
                    ) : null}
                </button>

                <Button size="sm" variant="outline">
                    <RefreshCw />
                    Refresh
                </Button>
            </div>
        </header>
    );
}

function Mark() {
    return (
        <span className="grid size-9 place-items-center rounded-md bg-primary text-primary-foreground">
            <svg width="18" height="18" viewBox="0 0 20 20" aria-hidden>
                <path d="M10 2.2 6.2 16.4 10 14l3.8 2.4Z" fill="currentColor" />
            </svg>
        </span>
    );
}
