"use client";

import { useEffect, useState } from "react";
import { Check, ImageOff, Star } from "lucide-react";

import { getTemplatePreview } from "@/services";
import { cn } from "@/util/helper";

/** The templates as cards. Picking one is picking the preference. */
export function TemplatePicker({ templates, selected, preferred, onSelect, disabled }) {
    return (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {templates.map((template) => (
                <TemplateCard
                    key={template.id}
                    template={template}
                    active={template.id === selected}
                    preferred={template.id === preferred}
                    onSelect={() => onSelect(template.id)}
                    disabled={disabled}
                />
            ))}
        </div>
    );
}

function TemplateCard({ template, active, preferred, onSelect, disabled }) {
    const preview = usePreview(template.has_preview ? template.id : null);

    return (
        <button
            type="button"
            onClick={onSelect}
            disabled={disabled}
            aria-pressed={active}
            className={cn(
                "panel group flex flex-col overflow-hidden text-left transition-shadow hover:shadow-raise",
                "outline-none focus-visible:ring-[3px] focus-visible:ring-ring/35",
                active && "ring-2 ring-primary",
                disabled && "pointer-events-none opacity-60"
            )}
        >
            <div className="relative aspect-[17/22] overflow-hidden bg-well">
                {preview ? (
                    // eslint-disable-next-line @next/next/no-img-element -- an object URL, not a file next/image can optimise
                    <img
                        src={preview}
                        alt={`${template.name} preview`}
                        className="size-full object-cover object-top"
                    />
                ) : (
                    <span className="flex size-full items-center justify-center text-muted-foreground">
                        <ImageOff className="size-5" />
                    </span>
                )}

                {active ? (
                    <span className="absolute right-2.5 top-2.5 grid size-6 place-items-center rounded-full bg-primary text-primary-foreground shadow-soft">
                        <Check className="size-[14px]" />
                    </span>
                ) : null}
            </div>

            <div className="flex items-center gap-2 border-t border-border px-4 py-3">
                <span className="truncate text-[13.5px] font-medium">{template.name}</span>
                {preferred ? (
                    <span
                        title="Your current preference"
                        className="inline-flex items-center gap-1 rounded-pill bg-primary-tint px-2 py-0.5 text-[11px] text-accent-foreground"
                    >
                        <Star className="size-[11px]" />
                        current
                    </span>
                ) : null}
                <span className="grow" />
                <span className="shrink-0 text-[11.5px] text-muted-foreground">
                    {template.style.skills}
                </span>
            </div>
        </button>
    );
}

/** The preview PNG needs the bearer token, so it is fetched and held as an object URL. */
function usePreview(templateId) {
    const [url, setUrl] = useState(null);

    useEffect(() => {
        if (!templateId) return undefined;

        let objectUrl = null;
        let cancelled = false;

        getTemplatePreview(templateId)
            .then((blob) => {
                if (cancelled) return;
                objectUrl = URL.createObjectURL(blob);
                setUrl(objectUrl);
            })
            .catch(() => {
                // A missing preview is a missing picture, not a broken screen.
            });

        return () => {
            cancelled = true;
            if (objectUrl) URL.revokeObjectURL(objectUrl);
        };
    }, [templateId]);

    return url;
}
