"use client";

import { useSelector } from "react-redux";
import { AlertTriangle, Check, Loader2, Save } from "lucide-react";
import { Button } from "@/component/ui/button";
import { selectDirty } from "@/store/profile/profileSlice";

/**
 * Saves the personal-details form. The sections below it have no save of their own to
 * wait for — each writes through as you edit it — so `dirty` tracks only this form.
 */
export function ProfileSaveBar({ status, isSubmitting }) {
    const dirty = useSelector(selectDirty);

    return (
        <div className="flex flex-wrap items-center gap-3">
            <span className="grow" />
            {status && !(status.ok && dirty) ? <Notice status={status} /> : null}
            {dirty && !status ? (
                <p className="text-[12.5px] text-muted-foreground">Unsaved changes</p>
            ) : null}
            <Button type="submit" size="sm" disabled={isSubmitting || !dirty}>
                {isSubmitting ? <Loader2 className="animate-spin" /> : <Save />}
                {isSubmitting ? "Saving" : "Save changes"}
            </Button>
        </div>
    );
}

function Notice({ status }) {
    return (
        <p
            className={
                status.ok
                    ? "flex items-center gap-2 rounded-sm bg-primary-tint px-3 py-2 text-[12.5px] text-accent-foreground"
                    : "flex items-start gap-2 rounded-sm bg-risk px-3 py-2 text-[12.5px] text-risk-ink"
            }
        >
            {status.ok ? (
                <Check className="size-[13px] shrink-0" />
            ) : (
                <AlertTriangle className="mt-0.5 size-[13px] shrink-0" />
            )}
            {status.message}
        </p>
    );
}
