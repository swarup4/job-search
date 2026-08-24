import Link from "next/link";
import { Building2, Clock, MapPin, Wallet } from "lucide-react";
import { MatchScore } from "@/component/MatchScore";
import { Signal } from "@/component/Signal";
import { ShortlistButton } from "@/component/ShortlistButton";
import { Badge } from "@/component/ui/badge";
import { Panel } from "@/component/ui/panel";
import { buttonVariants } from "@/component/ui/button";
import { ROUTES } from "@/routes";
import { cn } from "@/util/cn";

/**
 * The job row / card, shared by Search and Shortlist so the two can't drift.
 * `from` is the section the user is browsing — it rides along in every link so
 * the sidebar keeps that section highlighted.
 */
export function JobList({ jobs, view = "list", from }) {
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
        <Item key={job.id} job={job} from={from} />
      ))}
    </div>
  );
}

function ListRow({ job, from }) {
  return (
    <Panel hover className="p-5">
      <div className="flex flex-wrap items-center gap-x-5 gap-y-4">
        <span className="grid size-14 shrink-0 place-items-center rounded-md bg-secondary text-muted-foreground">
          <Building2 className="size-6" />
        </span>

        <div className="min-w-[230px] grow">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
            {/* the title is the way into the JD — no separate "View JD" button */}
            <Link
              href={ROUTES.job(job.id, from)}
              className="text-[16.5px] font-medium leading-tight hover:text-primary hover:underline hover:decoration-primary/40 hover:underline-offset-4"
            >
              {job.role}
            </Link>
            <Badge variant="source">{job.source}</Badge>
          </div>
          <p className="mt-1.5 text-[13.5px] text-muted-foreground">{job.company}</p>
          <div className="mt-2.5 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-[13px] text-muted-foreground">
            <Meta icon={MapPin}>{job.location}</Meta>
            <Meta icon={Clock}>{job.posted}</Meta>
            {job.salary ? <Meta icon={Wallet}>{job.salary}</Meta> : null}
            {job.mode ? <Badge variant="muted">{job.mode}</Badge> : null}
          </div>
        </div>

        <MatchScore value={job.match} size="lg" />

        <div className="flex shrink-0 flex-col items-end gap-2.5">
          {job.risks > 0 ? (
            <Signal kind="risk">
              {job.risks} risk {job.risks === 1 ? "flag" : "flags"}
            </Signal>
          ) : (
            <span className="text-[12px] text-muted-foreground">no risk flags</span>
          )}
          <div className="flex items-center gap-2">
            <ShortlistButton shortlisted={job.shortlisted} size="sm" />
            <Link
              href={ROUTES.keywords(job.id, from)}
              className={buttonVariants({ size: "sm" })}
            >
              Review
            </Link>
          </div>
        </div>
      </div>
    </Panel>
  );
}

function GridCard({ job, from }) {
  return (
    <Panel hover className="flex flex-col p-5">
      <div className="flex items-start gap-3">
        <span className="grid size-11 shrink-0 place-items-center rounded-md bg-secondary text-muted-foreground">
          <Building2 className="size-5" />
        </span>
        <div className="min-w-0 grow">
          <Link
            href={ROUTES.job(job.id, from)}
            className="text-[15px] font-medium leading-snug hover:text-primary hover:underline hover:decoration-primary/40 hover:underline-offset-4"
          >
            {job.role}
          </Link>
          <p className="mt-1 truncate text-[12.5px] text-muted-foreground">{job.company}</p>
        </div>
        <MatchScore value={job.match} size="sm" />
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
          {job.present} present · {job.missing} missing
        </span>
        <span className="grow" />
        <ShortlistButton shortlisted={job.shortlisted} size="sm" />
        <Link
          href={ROUTES.keywords(job.id, from)}
          className={buttonVariants({ variant: "soft", size: "sm" })}
        >
          Review
        </Link>
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
