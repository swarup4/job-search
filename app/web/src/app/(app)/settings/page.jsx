import { Database } from "lucide-react";
import { PageHeader } from "@/layout/PageHeader";
import { DiscoveryProvider } from "@/component/DiscoveryContext";
import { DiscoveryRunPanel } from "@/component/DiscoveryRunPanel";
import { DiscoverySources } from "@/component/DiscoverySources";
import { KV, ModelsPanel, SearchTargets } from "@/component/TierSettings";
import { Panel, PanelBody, PanelHeader, PanelTitle } from "@/component/ui/panel";

/**
 * Settings, as the system actually is: what discovery searches for, where it
 * searches, what its last run did, and which models see your text. Everything here
 * is read from the running tiers; Search targets saves with its own button and the
 * Sources switches save on their own.
 */
export default function Page() {
    return (
        <>
            <PageHeader
                title="Settings"
                subtitle="What discovery searches for, which companies it searches, and what its last run found."
            />

            <DiscoveryProvider>
                <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_340px]">
                    <div className="flex flex-col gap-5">
                        <SearchTargets />
                        <DiscoveryRunPanel />
                    </div>

                    {/* rail */}
                    <div className="flex flex-col gap-5">
                        <DiscoverySources />

                        <ModelsPanel />

                        <Panel>
                            <PanelHeader>
                                <Database className="size-[16px] text-primary" />
                                <PanelTitle>Stores</PanelTitle>
                            </PanelHeader>
                            <PanelBody className="flex flex-col gap-3 py-4">
                                <KV label="Database" value="MongoDB Atlas" />
                                <KV label="Vectors" value="same cluster" />
                                <KV label="Queue" value="none yet" />
                                <p className="border-t border-border pt-3 text-[12.5px] leading-relaxed text-muted-foreground">
                                    One cluster holds everything, scoped to your account. The AI tier has no
                                    database access and no credentials — it acts with your session&apos;s token.
                                </p>
                            </PanelBody>
                        </Panel>
                    </div>
                </div>
            </DiscoveryProvider>
        </>
    );
}
