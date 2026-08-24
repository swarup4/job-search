import Link from "next/link";
import { Info } from "lucide-react";
import { Panel } from "@/component/ui/panel";
import { ROUTES } from "@/routes";

/**
 * Chrome for the two pre-auth screens. They sit outside AppShell on purpose — no
 * sidebar, no topbar, nothing to navigate before you are in.
 *
 * The notice is here rather than duplicated per page because it is load-bearing: the
 * docs specify no auth (PRD §4, SRS §42), so these forms cannot sign anyone in and
 * must not imply otherwise.
 */
export function AuthShell({ title, subtitle, children, footer }) {
    return (
        <main className="grid min-h-screen place-items-center bg-background px-6 py-12">
            <div className="w-full max-w-[420px]">
                <Link href={ROUTES.board} className="flex items-center justify-center gap-2.5">
                    <span className="grid size-9 place-items-center rounded-md bg-primary text-primary-foreground">
                        <svg width="18" height="18" viewBox="0 0 20 20" aria-hidden>
                            <path d="M10 2.2 6.2 16.4 10 14l3.8 2.4Z" fill="currentColor" />
                        </svg>
                    </span>
                    <span className="text-[22px] font-bold tracking-tight">
                        Job<span className="text-primary">Pilot</span>
                    </span>
                </Link>

                <Panel className="mt-6 p-7">
                    <h1 className="text-[21px] font-semibold leading-tight tracking-tight">
                        {title}
                    </h1>
                    <p className="mt-1.5 text-[13.5px] leading-relaxed text-pretty text-muted-foreground">
                        {subtitle}
                    </p>
                    {children}
                </Panel>

                <div className="mt-4 flex items-start gap-2.5 rounded-sm border border-attention-rule bg-attention px-4 py-3">
                    <Info className="mt-0.5 size-[14px] shrink-0 text-attention-ink" />
                    <p className="text-[12.5px] leading-relaxed text-pretty text-attention-ink">
                        JobPilot is a single-user tool that runs on your own machine, so it has no
                        accounts and no auth service. This screen is interface only — filling it in
                        will not sign you in.
                    </p>
                </div>

                <p className="mt-5 text-center text-[13px] text-muted-foreground">{footer}</p>
            </div>
        </main>
    );
}
