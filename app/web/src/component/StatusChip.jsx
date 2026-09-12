import { cn } from "@/util/helper";

/** Variants come from the $statuses map in style/globals.scss. */
export function StatusChip({ status }) {
  return (
    <span className={cn("status-chip", `status-chip--${status.toLowerCase()}`)}>
      {status}
    </span>
  );
}
