"use client";

import { useSelector } from "react-redux";

import {
    selectCertifications,
    selectExperience,
    selectSkillCount,
} from "@/store/profile/profileSlice";

export function IndexedStats({ chunks }) {
    const roles = useSelector(selectExperience).length;
    const certs = useSelector(selectCertifications).length;
    const skills = useSelector(selectSkillCount);

    return (
        <div className="grid grid-cols-2 gap-3">
            <Stat n={chunks} label="chunks" />
            <Stat n={skills} label="skills" />
            <Stat n={roles} label="roles" />
            <Stat n={certs} label="certs" />
        </div>
    );
}

function Stat({ n, label }) {
    return (
        <div className="rounded-sm bg-well px-3.5 py-3">
            <div className="text-[21px] font-bold leading-none">{n}</div>
            <div className="mt-1.5 text-[12px] text-muted-foreground">{label}</div>
        </div>
    );
}
