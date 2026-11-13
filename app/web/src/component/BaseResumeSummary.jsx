"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { FileText } from "lucide-react";

import { ApiError, getBaseResume } from "@/services";
import { ROUTES } from "@/routes";

/** The template your default resume was built from, or a way to pick one. */
export function BaseResumeSummary() {
    // undefined while loading; null when no default resume has been submitted yet.
    const [resume, setResume] = useState(undefined);
    const [error, setError] = useState(null);

    useEffect(() => {
        let live = true;
        getBaseResume()
            .then((found) => live && setResume(found))
            .catch((failure) => {
                if (!live) return;
                setError(failure instanceof ApiError ? failure.message : "Could not read your resume.");
            });
        return () => {
            live = false;
        };
    }, []);

    if (error) return <p className="text-[12px] text-risk-ink">{error}</p>;

    return (
        <div className="flex items-center gap-2.5 rounded-sm bg-well px-3 py-2.5">
            <FileText className="size-[14px] shrink-0 text-muted-foreground" />
            {resume === undefined ? (
                <span className="text-[12px] text-muted-foreground">Loading…</span>
            ) : resume === null ? (
                <Link href={ROUTES.resume} className="text-[12px] text-primary hover:underline">
                    No template chosen yet — pick one
                </Link>
            ) : (
                <Link href={ROUTES.resumePreview} className="truncate text-[12px] hover:underline">
                    {resume.templateName}
                </Link>
            )}
        </div>
    );
}
