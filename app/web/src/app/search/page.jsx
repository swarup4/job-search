"use client";

import { useMemo, useState } from "react";
import { ChevronDown, ChevronUp, Search, SlidersHorizontal, X } from "lucide-react";
import { AppShell } from "@/layout/AppShell";
import { PageHeader } from "@/layout/PageHeader";
import { JobList } from "@/component/JobList";
import { ViewToggle } from "@/component/ViewToggle";
import { Panel, PanelBody } from "@/component/ui/panel";
import { Button } from "@/component/ui/button";
import { Field, Input } from "@/component/ui/field";
import { ROUTES } from "@/routes";
import search from "@/data/search.json";
import board from "@/data/board.json";
import { cn } from "@/util/cn";

const EMPTY = {
  keyword: "", company: "", location: "", title: "", skills: "",
  minMatch: "", type: "", mode: "", source: "", experience: "",
};

const LABEL = {
  keyword: "keyword", company: "company", location: "location", title: "title",
  skills: "skill", minMatch: "match ≥", type: "type", mode: "mode",
  source: "source", experience: "exp",
};

export default function Page() {
  const [q, setQ] = useState(EMPTY);
  const [advanced, setAdvanced] = useState(false);
  const [view, setView] = useState("list");

  const set = (k) => (e) => setQ({ ...q, [k]: e.target.value });
  const setPick = (k, v) => setQ({ ...q, [k]: q[k] === v ? "" : v });
  const active = Object.entries(q).filter(([, v]) => v !== "");

  const results = useMemo(() => {
    const t = (v) => (v || "").toLowerCase().trim();
    return search.results.filter((j) => {
      if (t(q.keyword) && ![j.role, j.company, j.location].some((f) => t(f).includes(t(q.keyword)))) return false;
      if (t(q.company) && !t(j.company).includes(t(q.company))) return false;
      if (t(q.location) && !t(j.location).includes(t(q.location))) return false;
      if (t(q.title) && !t(j.role).includes(t(q.title))) return false;
      if (q.minMatch && j.match < Number(q.minMatch)) return false;
      if (q.type && j.type !== q.type) return false;
      if (q.mode && j.mode !== q.mode) return false;
      if (q.source && j.source !== q.source) return false;
      if (q.experience && j.experience !== q.experience) return false;
      return true;
    });
  }, [q]);

  return (
    <AppShell
      active={ROUTES.search}
      counts={{
        pending: board.pending.keywordSelections + board.pending.applicationsToSubmit,
        shortlisted: search.shortlistedCount,
      }}
    >
      <PageHeader
        title="Search jobs"
        subtitle={`${search.totalIndexed} jobs indexed across all sources. Search any combination of fields.`}
      />

      <Panel className="p-5">
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)_minmax(0,1fr)_auto]">
          <Field label="Keyword">
            <div className="relative">
              <Search className="pointer-events-none absolute left-3.5 top-1/2 size-[15px] -translate-y-1/2 text-muted-foreground" />
              <Input className="pl-10" placeholder="Role, skill, anything" value={q.keyword} onChange={set("keyword")} />
            </div>
          </Field>
          <Field label="Company">
            <Input placeholder="e.g. Acme" value={q.company} onChange={set("company")} />
          </Field>
          <Field label="Location">
            <Input placeholder="e.g. Bengaluru" value={q.location} onChange={set("location")} />
          </Field>
          <div className="flex items-end">
            <Button className="h-11 w-full lg:w-auto">
              <Search />
              Search
            </Button>
          </div>
        </div>

        {advanced ? (
          <div className="mt-5 grid gap-4 border-t border-border pt-5 lg:grid-cols-4">
            <Field label="Job title">
              <Input placeholder="Exact title match" value={q.title} onChange={set("title")} />
            </Field>
            <Field label="Must mention skill">
              <Input placeholder="e.g. Kubernetes" value={q.skills} onChange={set("skills")} />
            </Field>
            <Field label="Minimum match %">
              <Input placeholder="e.g. 80" inputMode="numeric" value={q.minMatch} onChange={set("minMatch")} />
            </Field>
            <Field label="Experience band">
              <PickRow options={search.facets.experience} value={q.experience} onPick={(v) => setPick("experience", v)} />
            </Field>
            <Field label="Job type" className="lg:col-span-2">
              <PickRow options={search.facets.jobType} value={q.type} onPick={(v) => setPick("type", v)} />
            </Field>
            <Field label="Work mode">
              <PickRow options={search.facets.workMode} value={q.mode} onPick={(v) => setPick("mode", v)} />
            </Field>
            <Field label="Source">
              <PickRow options={search.facets.source} value={q.source} onPick={(v) => setPick("source", v)} />
            </Field>
          </div>
        ) : null}

        <div className="mt-4 flex flex-wrap items-center gap-3 border-t border-border pt-4">
          <button
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
                    key={k}
                    onClick={() => setQ({ ...q, [k]: "" })}
                    className="inline-flex items-center gap-1.5 rounded-sm bg-primary-tint px-2.5 py-1 text-[12px] text-accent-foreground hover:bg-primary hover:text-primary-foreground"
                  >
                    <span className="opacity-70">{LABEL[k] ?? k}:</span>
                    {v}
                    <X className="size-[11px]" />
                  </button>
                ))}
                <button onClick={() => setQ(EMPTY)} className="text-[12px] text-muted-foreground hover:text-primary">
                  clear all
                </button>
              </div>
            </>
          ) : null}
        </div>
      </Panel>

      <div className="mb-4 mt-6 flex flex-wrap items-center gap-3">
        <p className="text-[14px]">
          <span className="font-semibold">{results.length}</span>
          <span className="text-muted-foreground"> of {search.results.length} loaded jobs match</span>
        </p>
        <span className="grow" />
        <ViewToggle view={view} onChange={setView} />
      </div>

      {results.length === 0 ? (
        <Panel>
          <PanelBody className="py-14 text-center">
            <p className="text-[15px] font-medium">Nothing matches those fields</p>
            <p className="mx-auto mt-2 max-w-[46ch] text-[13.5px] text-muted-foreground">
              Try removing a filter chip above. Discovery only stores jobs that passed your
              minimum match, so a narrow search can legitimately return nothing.
            </p>
            <Button variant="outline" className="mt-5" onClick={() => setQ(EMPTY)}>
              Clear all fields
            </Button>
          </PanelBody>
        </Panel>
      ) : (
        <JobList jobs={results} view={view} from="search" />
      )}
    </AppShell>
  );
}

function PickRow({ options, value, onPick }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {options.map((o) => (
        <button
          key={o}
          onClick={() => onPick(o)}
          className={cn(
            "rounded-sm px-2.5 py-1.5 text-[12.5px] transition-colors",
            value === o ? "bg-primary text-primary-foreground" : "bg-secondary text-muted-foreground hover:text-foreground"
          )}
        >
          {o}
        </button>
      ))}
    </div>
  );
}
