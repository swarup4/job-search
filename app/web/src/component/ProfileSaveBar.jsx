"use client";

import { useSelector } from "react-redux";
import { Loader2, Save } from "lucide-react";
import { Button } from "@/component/ui/button";
import { selectDirty } from "@/store/profile/profileSlice";

/**
 * Saves the personal-details form. The sections below it have no save of their own to
 * wait for — each writes through as you edit it — so `dirty` tracks only this form.
 *
 * The outcome of a save is a toast, not a pill parked beside the button: it is news
 * about something that just happened, and it should not sit here until the form is
 * dirtied again. "Unsaved changes" stays, because that IS a standing state of the form.
 */
export function ProfileSaveBar({ isSubmitting }) {
    const dirty = useSelector(selectDirty);

    return (
        <div className="flex flex-wrap items-center gap-3">
            <span className="grow" />
            {dirty ? <p className="text-[12.5px] text-muted-foreground">Unsaved changes</p> : null}
            <Button type="submit" size="sm" disabled={isSubmitting || !dirty}>
                {isSubmitting ? <Loader2 className="animate-spin" /> : <Save />}
                {isSubmitting ? "Saving" : "Save changes"}
            </Button>
        </div>
    );
}
