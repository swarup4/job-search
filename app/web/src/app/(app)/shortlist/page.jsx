"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { AlertTriangle, Bookmark, Search } from "lucide-react";
import { PageHeader } from "@/layout/PageHeader";
import { JobList } from "@/component/JobList";
import { ViewToggle } from "@/component/ViewToggle";
import { Panel, PanelBody } from "@/component/ui/panel";
import { buttonVariants } from "@/component/ui/button";
import { Input } from "@/component/ui/field";
import {
  ApiError,
  getJob,
  getMatchSummaries,
  listApplications,
  unshortlistJob,
} from "@/services";
import { useRefreshShell } from "@/hooks/useShellCounts";
import { ROUTES } from "@/routes";

const SOURCE = { career_page: "Career page", linkedin: "LinkedIn", indeed: "Indeed", naukri: "Naukri", serpapi: "Google" };
const JOB_TYPE = { full_time: "Full time", contract: "Contract", part_time: "Part time", internship: "Internship" };
const WORK_MODE = { on_site: "On-site", hybrid: "Hybrid", remote: "Remote" };

/**
 * Your shortlisted applications, each with its job and match. Jobs you tailored or
 * applied to have moved on to the Pipeline's later columns and are not listed here.
 */
export default function Page() {
  const [view, setView] = useState("list");
  const [filter, setFilter] = useState("");
  const [data, setData] = useState({ status: "loading", saved: [] });
  const fetching = useRef(false);
  const refreshShell = useRefreshShell();

  const load = useCallback(async () => {
    try {
      const applications = await listApplications("shortlisted");
      const jobs = (await Promise.all(applications.map((row) => getJob(row.jobId)))).filter(Boolean);
      const summaries = await getMatchSummaries(jobs.map((job) => job.id));
      const byJob = new Map(summaries.map((summary) => [summary.jobId, summary]));
      setData({ status: "ready", saved: jobs.map((job) => toItem(job, byJob.get(job.id))) });
    } catch (failure) {
      setData({
        status: "error",
        saved: [],
        error: failure instanceof ApiError ? failure.message : "Could not load your shortlist.",
      });
    }
  }, []);

  useEffect(() => {
    // A ref, not state: React's development double-mount fires the effect twice.
    if (fetching.current) return;
    fetching.current = true;
    load();
  }, [load]);

  // Only removal happens here; a failed save rethrows so the bookmark snaps back.
  async function remove(job) {
    await unshortlistJob(job.id);
    setData((current) => ({ ...current, saved: current.saved.filter((item) => item.id !== job.id) }));
    refreshShell();
  }

  const { saved } = data;
  const jobs = useMemo(() => {
    const t = filter.toLowerCase().trim();
    if (!t) return saved;
    return saved.filter((j) =>
      [j.role, j.company, j.location].some((f) => f.toLowerCase().includes(t))
    );
  }, [saved, filter]);

  return (
    <>
      <PageHeader
        title="Shortlist"
        subtitle="Jobs you saved from a job page. Nothing lands here automatically."
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

      {data.status === "loading" ? (
        <p className="text-[13px] text-muted-foreground">Loading your shortlist…</p>
      ) : null}

      {data.status === "error" ? (
        <Panel className="flex items-start gap-2 px-5 py-4 text-[13px] text-risk-ink">
          <AlertTriangle className="mt-0.5 size-[14px] shrink-0" />
          {data.error}
        </Panel>
      ) : null}

      {data.status === "ready" && saved.length === 0 ? (
        <Panel>
          <PanelBody className="py-16 text-center">
            <span className="mx-auto grid size-12 place-items-center rounded-full bg-secondary text-muted-foreground">
              <Bookmark className="size-5" />
            </span>
            <p className="mt-4 text-[15px] font-medium">Your shortlist is empty</p>
            <p className="mx-auto mt-2 max-w-[46ch] text-[13.5px] text-muted-foreground">
              Save a job with the Shortlist button on its page, and it shows up here.
            </p>
            <Link href={ROUTES.board} className={buttonVariants({ className: "mt-5" })}>
              <Search />
              Browse the pipeline
            </Link>
          </PanelBody>
        </Panel>
      ) : null}

      {data.status === "ready" && saved.length > 0 ? (
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
            <JobList jobs={jobs} view={view} from="shortlist" onShortlist={remove} />
          )}
        </>
      ) : null}
    </>
  );
}

/** The shape JobList reads. */
function toItem(job, summary) {
  return {
    id: job.id,
    role: job.title,
    company: job.company,
    location: job.location,
    posted: ago(job.postedAt ?? job.discoveredAt),
    source: SOURCE[job.source] ?? job.source,
    type: JOB_TYPE[job.jobType] ?? null,
    mode: WORK_MODE[job.workMode] ?? null,
    salary: job.salaryText,
    match: summary?.score ?? 0,
    scored: Boolean(summary),
    risks: summary?.riskCount ?? 0,
    present: summary?.presentCount ?? 0,
    missing: summary?.missingCount ?? 0,
    shortlisted: true,
  };
}

function ago(timestamp) {
  if (!timestamp) return "recently";
  const minutes = Math.round((Date.now() - new Date(timestamp).getTime()) / 60000);
  if (minutes < 60) return minutes < 1 ? "just now" : `${minutes}m ago`;
  if (minutes < 60 * 24) return `${Math.round(minutes / 60)}h ago`;
  if (minutes < 60 * 24 * 30) return `${Math.round(minutes / (60 * 24))}d ago`;
  return new Date(timestamp).toLocaleDateString(undefined, { dateStyle: "medium" });
}
