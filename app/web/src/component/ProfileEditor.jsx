"use client";

import { useEffect, useRef } from "react";
import { useDispatch, useSelector } from "react-redux";
import { AlertTriangle, Loader2, RotateCw } from "lucide-react";

import { ApiError, getProfile } from "@/services";
import { Panel, PanelBody } from "@/component/ui/panel";
import { Button } from "@/component/ui/button";
import { ProfileIdentity } from "@/component/ProfileIdentity";
import { ExperienceSection } from "@/component/ExperienceSection";
import { EducationSection } from "@/component/EducationSection";
import { SkillsSection } from "@/component/SkillsSection";
import { CertificationsSection } from "@/component/CertificationsSection";
import {
    profileFailed,
    profileLoaded,
    profileLoading,
    profileReload,
    selectLoadError,
    selectStatus,
} from "@/store/profile/profileSlice";

/**
 * Loads My Details from the API and renders the editor once it is there.
 *
 * The fetch happens here rather than in the page because the bearer token lives in
 * sessionStorage, which only exists in the browser — the page itself renders on the
 * server. It is one request: `getProfile` is an aggregation that returns the account,
 * the personal details and the four lists together.
 *
 * The sections mount only when the data has arrived: each one seeds a Formik form
 * from the store, and Formik reads its initial values exactly once.
 */
export function ProfileEditor() {
    const status = useSelector(selectStatus);
    const error = useSelector(selectLoadError);
    const dispatch = useDispatch();

    // A ref, not `status`: the store updates a render too late to stop React's
    // development double-mount from firing the same requests twice. This flips
    // synchronously, so the second run sees it.
    const loading = useRef(false);

    useEffect(() => {
        // The store outlives navigation, so this runs once a session rather than on
        // every visit — returning to the page must not discard unsaved edits.
        if (status !== "idle" || loading.current) return;
        loading.current = true;
        dispatch(profileLoading());

        (async () => {
            try {
                dispatch(profileLoaded(await getProfile()));
            } catch (failure) {
                dispatch(
                    profileFailed(
                        failure instanceof ApiError
                            ? failure.message
                            : "Could not load your details."
                    )
                );
            } finally {
                // Cleared last, so "Try again" can start a fresh attempt.
                loading.current = false;
            }
        })();
        // No cleanup cancelling this: the result goes to the store, not to component
        // state, so it is still wanted if the page unmounts mid-flight.
    }, [status, dispatch]);

    if (status === "error") {
        return (
            <Panel>
                <PanelBody className="flex flex-col items-start gap-3 py-8">
                    <p className="flex items-start gap-2 text-[13px] text-risk-ink">
                        <AlertTriangle className="mt-0.5 size-[14px] shrink-0" />
                        {error}
                    </p>
                    <Button size="sm" variant="outline" onClick={() => dispatch(profileReload())}>
                        <RotateCw />
                        Try again
                    </Button>
                </PanelBody>
            </Panel>
        );
    }

    if (status !== "ready") {
        return (
            <Panel>
                <PanelBody className="flex items-center gap-2.5 py-8 text-[13px] text-muted-foreground">
                    <Loader2 className="size-[14px] animate-spin" />
                    Loading your details…
                </PanelBody>
            </Panel>
        );
    }

    return (
        <>
            <ProfileIdentity />
            <ExperienceSection />
            <EducationSection />
            <SkillsSection />
            <CertificationsSection />
        </>
    );
}
