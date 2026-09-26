"use client";

import { useCallback } from "react";
import { useDispatch } from "react-redux";

import { getShellCounts } from "@/services";
import { shellCountsLoaded } from "@/store/shell/shellSlice";

/**
 * Re-reads the header and sidebar badges. Call it after an action that changes them —
 * a shortlist toggle, a keyword choice, a finished analysis — rather than having each
 * page load its own copy.
 */
export function useRefreshShell() {
    const dispatch = useDispatch();
    return useCallback(async () => {
        const counts = await getShellCounts();
        if (counts) dispatch(shellCountsLoaded(counts));
    }, [dispatch]);
}
