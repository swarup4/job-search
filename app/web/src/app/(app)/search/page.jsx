"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { AlertTriangle, ChevronDown, ChevronUp, Loader2, Search, SlidersHorizontal, X } from "lucide-react";
import { PageHeader } from "@/layout/PageHeader";
import { JobList, toListItem } from "@/component/JobList";
import { ViewToggle } from "@/component/ViewToggle";
import { Panel, PanelBody } from "@/component/ui/panel";
import { Button } from "@/component/ui/button";
import { Field, Input } from "@/component/ui/field";
import { TokenInput } from "@/component/ui/token-input";
import { ApiError, searchJobs, setShortlisted } from "@/services";
import { useRefreshShell } from "@/hooks/useShellCounts";
import { cn } from "@/util/helper";

const PAGE = 20;

// `keywords` is a list — every one must appear in the description; the rest are text.
const EMPTY = {
  keywords: [], company: "", location: "", title: "", postedWithin: "",
};

const LABEL = {
  keywords: "keyword", company: "company", location: "location", title: "title",
  postedWithin: "posted",
};

const ADVANCED = ["title", "postedWithin"];

const POSTED_LABEL = { 1: "24 hours", 3: "3 days", 7: "7 days", 30: "30 days" };

/** A picked facet's value is the API's; the chip shows what the button said. */
const PICK_LABEL = { postedWithin: POSTED_LABEL };

/** A submitted search lives in the URL, so Back from a job — or the header's search box — reruns it. */
function fromParams(params) {
  const q = { ...EMPTY, keywords: params.getAll("keywords") };
  for (const key of Object.keys(EMPTY)) if (key !== "keywords") q[key] = params.get(key) ?? "";
  return q;
}

/** Keywords repeat (`keywords=python&keywords=mongodb`); every other field appears once. */
function toQueryString(q) {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(q)) {
    for (const one of [value].flat()) if (one !== "") params.append(key, one);
  }
  return params.toString();
}

// useSearchParams needs a boundary, or the page cannot prerender.
export default function Page() {
  return (
    <Suspense fallback={null}>
      <SearchJobs />
    </Suspense>
  );
}

const IDLE = { status: "idle", items: [], total: 0, indexed: null };

/**
 * Search over every stored job, on the API. Nothing is listed until a search is run;
 * editing the fields changes nothing until Search. The match ring and bookmark on each
 * row are yours — your score, your shortlist.
 */
function SearchJobs() {
  const params = useSearchParams();
  const [q, setQ] = useState(() => fromParams(params));
  // The search last run — what the results and the chips describe. Null before the first.
  const [applied, setApplied] = useState(null);
  const [advanced, setAdvanced] = useState(() => ADVANCED.some((key) => params.get(key)));
  const [view, setView] = useState("list");
  const [data, setData] = useState(IDLE);
  const [loadingMore, setLoadingMore] = useState(false);
  // Only the newest request may write results: a slow early answer must not win.
  const latest = useRef(0);
  // The query string this page last put in the URL.
  const written = useRef("");
  const refreshShell = useRefreshShell();

  const set = (k) => (e) => setQ({ ...q, [k]: e.target.value });
  const setPick = (k, v) => setQ({ ...q, [k]: q[k] === v ? "" : v });
  // One chip per filled field, and one per keyword.
  const active = Object.entries(applied ?? {}).flatMap(([key, value]) =>
    [value].flat().filter((one) => one !== "").map((one) => [key, one])
  );

  function writeUrl(query) {
    // Replaced, not pushed: Back should leave the page, not step through searches.
    // The History API rather than the router, so no navigation runs.
    written.current = query;
    window.history.replaceState(null, "", query ? `?${query}` : window.location.pathname);
  }

  const run = useCallback(
    async (query) => {
      const request = ++latest.current;
      setApplied(query);
      writeUrl(toQueryString(query));
      setData((current) => ({ ...current, status: "loading" }));
      try {
        const result = await searchJobs(query, { limit: PAGE });
        if (request !== latest.current) return;
        setData({ status: "ready", items: rowsFor(result.jobs), total: result.total, indexed: result.indexed });
      } catch (failure) {
        if (request !== latest.current) return;
        setData((current) => ({ ...current, status: "error", error: messageOf(failure) }));
      }
    },
    []
  );

  // A search in the URL — arriving with one, Back from a job, the header's search box —
  // fills the fields and runs. The page's own URL writes echo back here and are ignored.
  const paramString = params.toString();
  useEffect(() => {
    const incoming = fromParams(new URLSearchParams(paramString));
    const query = toQueryString(incoming);
    if (!query || query === written.current) return;
    setQ(incoming);
    if (ADVANCED.some((key) => incoming[key])) setAdvanced(true);
    run(incoming);
  }, [paramString, run]);

  /** Back to the empty start: no fields, no results, a bare URL. */
  function clearAll() {
    latest.current += 1;
    setQ(EMPTY);
    setApplied(null);
    setData(IDLE);
    writeUrl("");
  }

  /** A chip removes its field — or its one keyword — from the search that ran, and runs what is left. */
  function removeChip(key, value) {
    const without = (fields) => ({
      ...fields,
      [key]: key === "keywords" ? fields.keywords.filter((word) => word !== value) : "",
    });
    setQ(without);
    const next = without(applied);
    if (toQueryString(next)) run(next);
    else clearAll();
  }

  async function loadMore() {
    const request = latest.current;
    setLoadingMore(true);
    try {
      const result = await searchJobs(applied, { limit: PAGE, skip: data.items.length });
      const more = rowsFor(result.jobs);
      // The fields changed while this page was loading: it belongs to the old search.
      if (request !== latest.current) return;
      setData((current) => ({ ...current, items: [...current.items, ...more], total: result.total }));
    } catch (failure) {
      if (request !== latest.current) return;
      setData((current) => ({ ...current, status: "error", error: messageOf(failure) }));
    } finally {
      setLoadingMore(false);
    }
  }

  async function toggleShortlist(job, next) {
    await setShortlisted(job.id, next);
    refreshShell();
  }

  const { items, total, indexed } = data;
  const searching = data.status === "loading";

  return (
    <>
      <PageHeader
        title="Search jobs"
        subtitle={
          indexed == null
            ? "Search any combination of fields."
            : `${indexed} jobs indexed across all sources. Search any combination of fields.`
        }
      />

      <Panel className="p-5">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            run(q);
          }}
          className="grid gap-4 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)_minmax(0,1fr)_auto]"
        >
          <Field label="Keywords">
            <TokenInput
              items={q.keywords}
              onChange={(keywords) => setQ({ ...q, keywords })}
              onEnterEmpty={() => run(q)}
              placeholder="e.g. Python — press Enter to add"
            />
          </Field>
          <Field label="Company">
            <Input placeholder="e.g. Accenture" value={q.company} onChange={set("company")} />
          </Field>
          <Field label="Location">
            <Input placeholder="e.g. Bengaluru" value={q.location} onChange={set("location")} />
          </Field>
          <div className="flex items-end">
            <Button type="submit" className="h-11 w-full lg:w-auto" disabled={searching}>
              {searching ? <Loader2 className="animate-spin" /> : <Search />}
              Search
            </Button>
          </div>
        </form>

        {advanced ? (
          <div className="mt-5 grid gap-4 border-t border-border pt-5 lg:grid-cols-2">
            <Field label="Job title">
              <Input placeholder="Words in the title" value={q.title} onChange={set("title")} />
            </Field>
            <Field label="Posted within">
              <PickRow labels={POSTED_LABEL} value={q.postedWithin} onPick={(v) => setPick("postedWithin", v)} />
            </Field>
          </div>
        ) : null}

        <div className="mt-4 flex flex-wrap items-center gap-3 border-t border-border pt-4">
          <button
            type="button"
            onClick={() => setAdvanced(!advanced)}
            className="inline-flex items-center gap-1.5 text-[13px] font-medium text-primary hover:underline"
          >
            <SlidersHorizontal className="size-[14px]" />
            {advanced ? "Fewer fields" : "More fields"}
            {advanced ? <ChevronUp className="size-[14px]" /> : <ChevronDown className="size-[14px]" />}
          </button>

          {active.length > 0 ? (
            <>
              <span className="h-4 w-px bg-border" />
              <div className="flex flex-wrap items-center gap-2">
                {active.map(([k, v]) => (
                  <button
                    key={`${k}:${v}`}
                    type="button"
                    onClick={() => removeChip(k, v)}
                    className="inline-flex items-center gap-1.5 rounded-sm bg-primary-tint px-2.5 py-1 text-[12px] text-accent-foreground hover:bg-primary hover:text-primary-foreground"
                  >
                    <span className="opacity-70">{LABEL[k] ?? k}:</span>
                    {PICK_LABEL[k]?.[v] ?? v}
                    <X className="size-[11px]" />
                  </button>
                ))}
                <button type="button" onClick={clearAll} className="text-[12px] text-muted-foreground hover:text-primary">
                  clear all
                </button>
              </div>
            </>
          ) : null}
        </div>
      </Panel>

      {data.status === "idle" ? (
        <Panel className="mt-6">
          <PanelBody className="py-14 text-center">
            <span className="mx-auto grid size-12 place-items-center rounded-full bg-secondary text-muted-foreground">
              <Search className="size-5" />
            </span>
            <p className="mt-4 text-[15px] font-medium">Search to see jobs</p>
            <p className="mx-auto mt-2 max-w-[46ch] text-[13.5px] text-muted-foreground">
              Fill in any fields above and press Search. Leave them all empty to list every job.
            </p>
          </PanelBody>
        </Panel>
      ) : (
        <div className="mb-4 mt-6 flex flex-wrap items-center gap-3">
          {searching && data.indexed == null ? (
            <p className="text-[14px] text-muted-foreground">Searching…</p>
          ) : (
            <p className="text-[14px]">
              <span className="font-semibold">{total}</span>
              <span className="text-muted-foreground">
                {" "}job{total === 1 ? "" : "s"} match{total === 1 ? "es" : ""}
                {items.length < total ? ` · showing ${items.length}` : ""}
              </span>
            </p>
          )}
          {searching ? <Loader2 className="size-[14px] animate-spin text-muted-foreground" /> : null}
          <span className="grow" />
          <ViewToggle view={view} onChange={setView} />
        </div>
      )}

      {data.status === "error" ? (
        <Panel className="mb-4 flex items-start gap-2 px-5 py-4 text-[13px] text-risk-ink">
          <AlertTriangle className="mt-0.5 size-[14px] shrink-0" />
          {data.error}
        </Panel>
      ) : null}

      {data.status === "ready" && items.length === 0 ? (
        <Panel>
          <PanelBody className="py-14 text-center">
            <p className="text-[15px] font-medium">Nothing matches those fields</p>
            <p className="mx-auto mt-2 max-w-[46ch] text-[13.5px] text-muted-foreground">
              Try removing a filter chip above, or a shorter word.
            </p>
            <Button variant="outline" className="mt-5" onClick={clearAll}>
              Clear all fields
            </Button>
          </PanelBody>
        </Panel>
      ) : null}

      {items.length > 0 ? (
        <>
          <JobList jobs={items} view={view} from="search" onShortlist={toggleShortlist} />
          {items.length < total ? (
            <div className="mt-5 flex justify-center">
              <Button variant="outline" onClick={loadMore} disabled={loadingMore || searching}>
                {loadingMore ? <Loader2 className="animate-spin" /> : null}
                {loadingMore ? "Loading…" : `Load more (${total - items.length} left)`}
              </Button>
            </div>
          ) : null}
        </>
      ) : null}
    </>
  );
}

/** Each result already carries your score and shortlist, so a row is just its reshaping. */
function rowsFor(jobs) {
  return jobs.map((hit) =>
    toListItem(hit, hit.score == null ? null : hit, { shortlisted: hit.shortlisted })
  );
}

function PickRow({ labels, value, onPick }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {Object.entries(labels).map(([key, label]) => (
        <button
          key={key}
          type="button"
          onClick={() => onPick(key)}
          className={cn(
            "rounded-sm px-2.5 py-1.5 text-[12.5px] transition-colors",
            value === key ? "bg-primary text-primary-foreground" : "bg-secondary text-muted-foreground hover:text-foreground"
          )}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

function messageOf(failure) {
  return failure instanceof ApiError ? failure.message : "Could not search jobs.";
}
