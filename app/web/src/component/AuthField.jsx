"use client";

import { useState } from "react";
import { Eye, EyeOff } from "lucide-react";
import { Input } from "@/component/ui/field";

/** Labelled input; a password variant gets a reveal toggle. */
export function AuthField({ label, type = "text", value, onChange, ...props }) {
    const [revealed, setRevealed] = useState(false);
    const isPassword = type === "password";

    return (
        <label className="flex flex-col gap-2">
            <span className="text-[13px] font-medium">{label}</span>
            <span className="relative block">
                <Input
                    type={isPassword && revealed ? "text" : type}
                    value={value}
                    onChange={(e) => onChange(e.target.value)}
                    className={isPassword ? "pr-11" : undefined}
                    {...props}
                />
                {isPassword ? (
                    <button
                        type="button"
                        onClick={() => setRevealed((r) => !r)}
                        aria-label={revealed ? "Hide password" : "Show password"}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    >
                        {revealed ? <EyeOff className="size-[15px]" /> : <Eye className="size-[15px]" />}
                    </button>
                ) : null}
            </span>
        </label>
    );
}
