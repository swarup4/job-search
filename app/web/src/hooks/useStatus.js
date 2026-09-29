"use client";

import { useCallback } from "react";
import { useDispatch } from "react-redux";

import { getStatus } from "@/services";
import { statusLoaded } from "@/store/status/statusSlice";

/**
 * Re-reads `GET /api/status` into the store. Call it after an action that changes a
 * number — a shortlist toggle, a keyword choice, a finished run — rather than having each
 * page load its own copy.
 */
export function useRefreshStatus() {
    const dispatch = useDispatch();
    return useCallback(async () => {
        const status = await getStatus();
        if (status) dispatch(statusLoaded(status));
    }, [dispatch]);
}
