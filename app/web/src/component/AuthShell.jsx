import Link from "next/link";
import { Panel } from "@/component/ui/panel";
import { ROUTES } from "@/routes";

/**
 * Chrome for the two pre-auth screens. They sit outside AppShell on purpose — no
 * sidebar, no topbar, nothing to navigate before you are in.
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

                <p className="mt-5 text-center text-[13px] text-muted-foreground">{footer}</p>
            </div>
        </main>
    );
}
