import { Sidebar } from "@/layout/Sidebar";
import { Topbar } from "@/layout/Topbar";

export function AppShell({ active, children, counts = {}, aside = true }) {
    return (
        <div className="min-h-screen bg-background">
            <Topbar pending={counts.pending} />
            <div className="mx-auto flex max-w-[1560px] gap-5 px-6 py-6">
                {aside ? <Sidebar active={active} counts={counts} /> : null}
                <main className="min-w-0 grow">{children}</main>
            </div>
        </div>
    );
}
