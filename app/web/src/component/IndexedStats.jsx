"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useSelector } from "react-redux";
import { AlertTriangle, RefreshCw } from "lucide-react";

import { ApiError, getIndexStats, reindexProfile } from "@/services";
import { Button } from "@/component/ui/button";
import {
    selectCertifications,
    selectExperience,
    selectSkillCount,
} from "@/store/profile/profileSlice";

/**
 * The "Indexed for retrieval" panel, on real numbers.
 *
 * `chunks` and `pending` come from the server; the other three are counts of what is
 * on screen and come from the store. Pending is shown rather than folded into the
 * total because it is the honest state of the index: the server re-cuts the profile
 * on every edit, but only the AI tier can embed, and a chunk with no vector is not
 * retrievable yet.
 */
export function IndexedStats() {
    const roles = useSelector(selectExperience).length;
    const certs = useSelector(selectCertifications).length;
    const skills = useSelector(selectSkillCount);

    const [stats, setStats] = useState(null);
    const [error, setError] = useState(null);
    const [busy, setBusy] = useState(false);
    // A ref, not `busy`: React's development double-mount fires the effect twice
    // before any state update lands.
    const loading = useRef(false);

    const load = useCallback(async (call) => {
        if (loading.current) return;
        loading.current = true;
        setError(null);
        try {
            setStats(await call());
        } catch (failure) {
            setError(failure instanceof ApiError ? failure.message : "Could not read the index.");
        } finally {
            loading.current = false;
        }
    }, []);

    useEffect(() => {
        load(getIndexStats);
    }, [load]);

    async function reindex() {
        setBusy(true);
        await load(reindexProfile);
        setBusy(false);
    }

    return (
        <>
            <div className="grid grid-cols-2 gap-3">
                <Stat n={stats?.chunks ?? "—"} label="chunks" />
                <Stat n={skills} label="skills" />
                <Stat n={roles} label="roles" />
                <Stat n={certs} label="certs" />
            </div>

            <p className="text-[12.5px] leading-relaxed text-muted-foreground">
                Everything above is chunked and embedded so the match agent can find it. Editing a
                section re-cuts it here; the new text is not retrievable until it has been embedded.
            </p>

            <Button variant="outline" size="sm" className="w-full" onClick={reindex} disabled={busy}>
                <RefreshCw className={busy ? "animate-spin" : undefined} />
                {busy ? "Re-indexing…" : "Re-index now"}
            </Button>

            <Footer stats={stats} error={error} />
        </>
    );
}

function Footer({ stats, error }) {
    if (error) {
        return (
            <p className="flex items-start justify-center gap-1.5 text-center text-[12px] text-risk-ink">
                <AlertTriangle className="mt-0.5 size-[12px] shrink-0" />
                {error}
            </p>
        );
    }

    return (
        <p className="text-center text-[12px] text-muted-foreground">{describe(stats)}</p>
    );
}

function describe(stats) {
    if (!stats) return "reading the index…";
    if (stats.chunks === 0) return "nothing indexed yet";
    if (stats.pending > 0) return `${stats.pending} waiting to be embedded`;
    return `last indexed ${when(stats.lastIndexedAt)}`;
}

function when(timestamp) {
    return new Date(timestamp).toLocaleString(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
    });
}

function Stat({ n, label }) {
    return (
        <div className="rounded-sm bg-well px-3.5 py-3">
            <div className="text-[21px] font-bold leading-none">{n}</div>
            <div className="mt-1.5 text-[12px] text-muted-foreground">{label}</div>
        </div>
    );
}
