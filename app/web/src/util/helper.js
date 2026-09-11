/**
 * Small pure helpers shared across the app. Nothing here may import React or touch
 * the DOM — that is what keeps it safe to call from anywhere: server components,
 * client components and plain services alike.
 */

import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/** Merge Tailwind classes so a later class wins over an earlier one it conflicts with. */
export function cn(...inputs) {
    return twMerge(clsx(inputs));
}

/** Avatar initials: "Swarup Saha" -> "SS". Two at most, so the square never overflows. */
export function initials(name) {
    const letters = (name ?? "")
        .split(" ")
        .filter(Boolean)
        .slice(0, 2)
        .map((word) => word[0].toUpperCase())
        .join("");

    // An avatar with nothing in it reads as a broken image rather than a missing name.
    return letters || "?";
}

export const MONTHS = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

/** Marks a role still in progress; stored in `end` rather than as a null. */
export const PRESENT = "Present";

/** "Mar 2021" -> { month: "Mar", year: "2021" }. A bare year keeps the month empty. */
export function splitMonthYear(value) {
    const parts = (value ?? "").trim().split(/\s+/);
    if (parts.length === 2 && MONTHS.includes(parts[0])) {
        return { month: parts[0], year: parts[1] };
    }
    if (parts.length === 1 && /^\d{4}$/.test(parts[0])) {
        return { month: "", year: parts[0] };
    }
    return { month: "", year: "" };
}

export function joinMonthYear(month, year) {
    const y = (year ?? "").trim();
    if (!y) return "";
    return month ? `${month} ${y}` : y;
}
