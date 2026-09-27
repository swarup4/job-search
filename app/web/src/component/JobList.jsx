import Link from "next/link";
import { Building2, Clock, MapPin, Wallet } from "lucide-react";
import { MatchScore } from "@/component/MatchScore";
import { Signal } from "@/component/Signal";
import { ShortlistButton } from "@/component/ShortlistButton";
import { Badge } from "@/component/ui/badge";
import { Panel } from "@/component/ui/panel";
import { Tooltip } from "@/component/ui/tooltip";
import { buttonVariants } from "@/component/ui/button";
import { ROUTES } from "@/routes";

const SOURCE_LABEL = {
  career_page: "Career page",
  linkedin: "LinkedIn",
  indeed: "Indeed",
  naukri: "Naukri",
  serpapi: "Google",
};
const JOB_TYPE_LABEL = {
  full_time: "Full time",
  contract: "Contract",
  part_time: "Part time",
  internship: "Internship",
};
const WORK_MODE_LABEL = { on_site: "On-site", hybrid: "Hybrid", remote: "Remote" };

/**
 * `onShortlist(job, next)`, if given, saves the bookmark; without it the bookmark is
 * local only, as on the screens still on fixtures. A job with `scored: false` shows no
 * match ring and no Review link — there is nothing to review yet.
 */
export function JobList({ jobs, view = "list", from, onShortlist }) {
  const Item = view === "grid" ? GridCard : ListRow;
  return (
    <div
      className={
        view === "grid"
          ? "grid gap-4 md:grid-cols-2 xl:grid-cols-3"
          : "flex flex-col gap-4"
      }
    >
      {jobs.map((job) => (
        <Item key={job.id} job={job} from={from} onShortlist={onShortlist} />
      ))}
    </div>
  );
}

function ListRow({ job, from, onShortlist }) {
  return (
    <Panel hover className="p-5">
      {/* From md up the row never wraps: a long title shrinks the middle column rather
          than pushing the score and bookmark onto a line of their own. */}
      <div className="flex flex-wrap items-center gap-x-5 gap-y-4 md:flex-nowrap">
        <span className="grid size-14 shrink-0 place-items-center rounded-md bg-secondary text-muted-foreground">
          <Building2 className="size-6" />
        </span>

        <div className="min-w-[230px] grow md:min-w-0 md:basis-0">
          <Tooltip content={job.role} onlyWhenTruncated>
            {/* No hover underline: line-clamp's overflow would clip it under the last line. */}
            <Link
              href={ROUTES.job(job.id, from)}
              className="line-clamp-2 text-[16.5px] font-medium leading-tight hover:text-primary"
            >
              {job.role}
            </Link>
          </Tooltip>
          <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1">
            <p className="text-[13.5px] text-muted-foreground">{job.company}</p>
            <Badge variant="source">{job.source}</Badge>
          </div>
          <div className="mt-2.5 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-[13px] text-muted-foreground">
            <Meta icon={MapPin}>{job.location}</Meta>
            <Meta icon={Clock}>{job.posted}</Meta>
            {job.salary ? <Meta icon={Wallet}>{job.salary}</Meta> : null}
            {job.mode ? <Badge variant="muted">{job.mode}</Badge> : null}
          </div>
        </div>

        {job.scored === false ? null : <MatchScore value={job.match} size="lg" />}

        <div className="flex shrink-0 flex-col items-end gap-2.5">
          {job.scored === false ? (
            <span className="text-[12px] text-muted-foreground">not scored yet</span>
          ) : job.risks > 0 ? (
            <Signal kind="risk">
              {job.risks} risk {job.risks === 1 ? "flag" : "flags"}
            </Signal>
          ) : (
            <span className="text-[12px] text-muted-foreground">no risk flags</span>
          )}
          <div className="flex items-center gap-2">
            <ShortlistButton
              shortlisted={job.shortlisted}
              size="sm"
              onToggle={onShortlist ? (next) => onShortlist(job, next) : undefined}
            />
            {job.scored === false ? null : (
              <Link
                href={ROUTES.keywords(job.id, from)}
                className={buttonVariants({ size: "sm" })}
              >
                Review
              </Link>
            )}
          </div>
        </div>
      </div>
    </Panel>
  );
}

function GridCard({ job, from, onShortlist }) {
  return (
    <Panel hover className="flex flex-col p-5">
      <div className="flex items-start gap-3">
        <span className="grid size-11 shrink-0 place-items-center rounded-md bg-secondary text-muted-foreground">
          <Building2 className="size-5" />
        </span>
        <div className="min-w-0 grow">
          <Tooltip content={job.role} onlyWhenTruncated>
            <Link
              href={ROUTES.job(job.id, from)}
              className="line-clamp-2 text-[15px] font-medium leading-snug hover:text-primary"
            >
              {job.role}
            </Link>
          </Tooltip>
          <p className="mt-1 truncate text-[12.5px] text-muted-foreground">{job.company}</p>
        </div>
        {job.scored === false ? null : <MatchScore value={job.match} size="sm" />}
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-x-3 gap-y-2 text-[12.5px] text-muted-foreground">
        <Meta icon={MapPin} sm>{job.location}</Meta>
        <Meta icon={Clock} sm>{job.posted}</Meta>
      </div>

      <div className="mt-3 flex flex-wrap gap-1.5">
        {job.type ? <Badge variant="muted">{job.type}</Badge> : null}
        {job.mode ? <Badge variant="muted">{job.mode}</Badge> : null}
        <Badge variant="source">{job.source}</Badge>
      </div>

      {job.salary ? (
        <p className="mt-3 text-[13px] text-muted-foreground">{job.salary}</p>
      ) : null}

      {job.risks > 0 ? (
        <div className="mt-3">
          <Signal kind="risk">
            {job.risks} risk {job.risks === 1 ? "flag" : "flags"}
          </Signal>
        </div>
      ) : null}

      <div className="grow" />

      <div className="mt-4 flex items-center gap-2 border-t border-border pt-4">
        <span className="text-[12.5px] text-muted-foreground">
          {job.scored === false ? "not scored yet" : `${job.present} present · ${job.missing} missing`}
        </span>
        <span className="grow" />
        <ShortlistButton
          shortlisted={job.shortlisted}
          size="sm"
          onToggle={onShortlist ? (next) => onShortlist(job, next) : undefined}
        />
        {job.scored === false ? null : (
          <Link
            href={ROUTES.keywords(job.id, from)}
            className={buttonVariants({ variant: "soft", size: "sm" })}
          >
            Review
          </Link>
        )}
      </div>
    </Panel>
  );
}

function Meta({ icon: Icon, children, sm }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <Icon className={sm ? "size-[12px]" : "size-[13px]"} />
      {children}
    </span>
  );
}

/** An API job and its match summary (absent when unscored) as the shape JobList reads. */
export function toListItem(job, summary, { shortlisted = false } = {}) {
  return {
    id: job.id,
    role: job.title,
    company: job.company,
    location: job.location,
    posted: ago(job.postedAt ?? job.discoveredAt),
    source: SOURCE_LABEL[job.source] ?? job.source,
    type: JOB_TYPE_LABEL[job.jobType] ?? null,
    mode: WORK_MODE_LABEL[job.workMode] ?? null,
    salary: job.salaryText,
    match: summary?.score ?? 0,
    scored: Boolean(summary),
    risks: summary?.riskCount ?? 0,
    present: summary?.presentCount ?? 0,
    missing: summary?.missingCount ?? 0,
    shortlisted,
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
