"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useSelector } from "react-redux";
import { Bell, RefreshCw, Search } from "lucide-react";
import { Button } from "@/component/ui/button";
import { SignOutButton } from "@/component/SignOutButton";
import { useScoringRun } from "@/hooks/useScoringRun";
import { useRefreshStatus } from "@/hooks/useStatus";
import { ROUTES } from "@/routes";
import { selectStatus } from "@/store/status/statusSlice";

export function Topbar() {
    const { badges, syncedAt } = useSelector(selectStatus);
    const { pending } = badges;
    const refreshStatus = useRefreshStatus();
    const router = useRouter();
    const [term, setTerm] = useState("");
    const [refreshing, setRefreshing] = useState(false);
    // Re-render every half minute so "Synced …" keeps counting up.
    const [, tick] = useState(0);
    useEffect(() => {
        const timer = setInterval(() => tick((n) => n + 1), 30_000);
        return () => clearInterval(timer);
    }, []);

    const scoring = useScoringRun(refreshStatus);

    // Re-reads the badges, and scores every job that has no match yet — or, while
    // that run is going, says how far it has got.
    async function refresh() {
        setRefreshing(true);
        try {
            await Promise.all([refreshStatus(), scoring.trigger()]);
        } finally {
            setRefreshing(false);
        }
    }

    return (
        <header className="sticky top-0 z-20 border-b border-border bg-card">
            <div className="mx-auto flex h-[68px] max-w-[1560px] items-center gap-5 px-6">
                <Link href={ROUTES.board} className="flex items-center gap-2.5">
                    <Mark />
                    <span className="text-[20px] font-bold tracking-tight">
                        Job<span className="text-primary">Pilot</span>
                    </span>
                </Link>

                {/* Hands the words to the Search page as one keyword; the page does the rest. */}
                <form
                    role="search"
                    onSubmit={(e) => {
                        e.preventDefault();
                        const keyword = term.trim();
                        router.push(keyword ? `${ROUTES.search}?keywords=${encodeURIComponent(keyword)}` : ROUTES.search);
                    }}
                    className="ml-4 hidden max-w-[420px] grow items-center gap-2.5 rounded-pill bg-secondary px-4 py-2.5 md:flex"
                >
                    <Search className="size-[15px] shrink-0 text-muted-foreground" />
                    <input
                        value={term}
                        onChange={(e) => setTerm(e.target.value)}
                        placeholder="Search roles, companies, keywords"
                        aria-label="Search jobs"
                        className="w-full bg-transparent text-[14px] outline-none placeholder:text-muted-foreground"
                    />
                </form>

                <div className="grow" />

                {syncedAt ? (
                    <span className="hidden text-[13px] text-muted-foreground lg:inline">
                        Synced {ago(syncedAt)}
                    </span>
                ) : null}

                <button className="relative grid size-10 place-items-center rounded-pill hover:bg-secondary">
                    <Bell className="size-[17px] text-muted-foreground" />
                    {pending > 0 ? (
                        <span className="absolute right-1.5 top-1.5 grid size-[17px] place-items-center rounded-full bg-attention-solid text-[10px] font-bold text-white">
                            {pending}
                        </span>
                    ) : null}
                </button>

                <Button
                    size="sm"
                    variant="outline"
                    onClick={refresh}
                    disabled={refreshing}
                    title="Refresh the counts and score every job that has no match yet"
                >
                    <RefreshCw className={refreshing || scoring.running ? "animate-spin" : undefined} />
                    {scoring.running ? "Scoring…" : "Refresh"}
                </Button>

                <SignOutButton />
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

function ago(timestamp) {
    const minutes = Math.floor((Date.now() - timestamp) / 60000);
    if (minutes < 1) return "just now";
    if (minutes < 60) return `${minutes} min ago`;
    return `${Math.floor(minutes / 60)}h ago`;
}
