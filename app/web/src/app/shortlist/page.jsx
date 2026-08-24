"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { Bookmark, Search } from "lucide-react";
import { AppShell } from "@/layout/AppShell";
import { PageHeader } from "@/layout/PageHeader";
import { JobList } from "@/component/JobList";
import { ViewToggle } from "@/component/ViewToggle";
import { Panel, PanelBody } from "@/component/ui/panel";
import { buttonVariants } from "@/component/ui/button";
import { Field, Input } from "@/component/ui/field";
import { ROUTES } from "@/routes";
import search from "@/data/search.json";
import board from "@/data/board.json";

/**
 * The jobs you saved — the same list shape as Search, filtered to `shortlisted`.
 * Both pages render JobList, so a row looks identical wherever you meet it.
 */
export default function Page() {
  const [view, setView] = useState("list");
  const [filter, setFilter] = useState("");

  const saved = useMemo(() => search.results.filter((j) => j.shortlisted), []);
  const jobs = useMemo(() => {
    const t = filter.toLowerCase().trim();
    if (!t) return saved;
    return saved.filter((j) =>
      [j.role, j.company, j.location].some((f) => f.toLowerCase().includes(t))
    );
  }, [saved, filter]);

  return (
    <AppShell
      active={ROUTES.shortlist}
      counts={{
        pending: board.pending.keywordSelections + board.pending.applicationsToSubmit,
        shortlisted: saved.length,
      }}
    >
      <PageHeader
        title="Shortlist"
        subtitle="Jobs you saved from Search or from a job page. Nothing lands here automatically."
      >
        <div className="flex items-center gap-2.5">
          <div className="w-[240px]">
            <Input
              placeholder="Filter your shortlist"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
            />
          </div>
          <ViewToggle view={view} onChange={setView} />
        </div>
      </PageHeader>

      {saved.length === 0 ? (
        <Panel>
          <PanelBody className="py-16 text-center">
            <span className="mx-auto grid size-12 place-items-center rounded-full bg-secondary text-muted-foreground">
              <Bookmark className="size-5" />
            </span>
            <p className="mt-4 text-[15px] font-medium">Your shortlist is empty</p>
            <p className="mx-auto mt-2 max-w-[46ch] text-[13.5px] text-muted-foreground">
              Save a job with the bookmark button on Search or on a job page, and it shows up here.
            </p>
            <Link href={ROUTES.search} className={buttonVariants({ className: "mt-5" })}>
              <Search />
              Search jobs
            </Link>
          </PanelBody>
        </Panel>
      ) : (
        <>
          <div className="mb-4 flex flex-wrap items-center gap-3">
            <p className="text-[14px]">
              <span className="font-semibold">{jobs.length}</span>
              <span className="text-muted-foreground">
                {jobs.length === saved.length ? " saved" : ` of ${saved.length} saved`} job
                {jobs.length === 1 ? "" : "s"}
              </span>
            </p>
          </div>
          {jobs.length === 0 ? (
            <Panel>
              <PanelBody className="py-12 text-center">
                <p className="text-[14px] text-muted-foreground">
                  Nothing in your shortlist matches “{filter}”.
                </p>
              </PanelBody>
            </Panel>
          ) : (
            <JobList jobs={jobs} view={view} from="shortlist" />
          )}
        </>
      )}
    </AppShell>
  );
}
