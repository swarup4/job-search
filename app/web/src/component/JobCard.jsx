import Link from "next/link";
import { Building2, Clock, FileText, MapPin } from "lucide-react";
import { MatchScore } from "@/component/MatchScore";
import { Signal } from "@/component/Signal";
import { ROUTES } from "@/routes";

export function JobCard({ card, from = "board" }) {
    return (
        <Link href={ROUTES.job(card.id, from)} className="panel block p-4 transition-shadow hover:shadow-raise">
            <div className="flex items-start gap-3">
                <span className="grid size-10 shrink-0 place-items-center rounded-md bg-secondary text-muted-foreground">
                    <Building2 className="size-[17px]" />
                </span>
                <div className="min-w-0 grow">
                    <h3 className="truncate text-[14px] font-medium leading-snug">{card.role}</h3>
                    <p className="mt-1 truncate text-[12.5px] text-muted-foreground">{card.company}</p>
                </div>
                {card.match ? <MatchScore value={card.match} size="sm" /> : null}
            </div>

            {card.meta ? (
                <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1.5 text-[12px] text-muted-foreground">
                    <span className="inline-flex items-center gap-1">
                        <MapPin className="size-[12px]" />
                        {card.meta.split(" · ")[0]}
                    </span>
                    {card.meta.split(" · ")[1] ? (
                        <span className="inline-flex items-center gap-1">
                            <Clock className="size-[12px]" />
                            {card.meta.split(" · ").slice(1).join(" · ")}
                        </span>
                    ) : null}
                </div>
            ) : null}

            {card.flag ? <div className="mt-3">
                <Signal kind={card.flag.kind}>{card.flag.text}</Signal>
            </div> : null}

            {card.file ? (
                <div className="mt-3 inline-flex items-center gap-1.5 rounded-sm bg-secondary px-2 py-1 font-mono text-[11px] text-muted-foreground">
                    <FileText className="size-[11px]" />
                    {card.file}
                </div>
            ) : null}
        </Link>
    );
}
