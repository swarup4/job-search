import { useState } from "react";

import { askWorker } from "@/shared/messages";
import type { AccountRead } from "@/shared/types";

export function SignIn({ onSignedIn }: { onSignedIn: (account: AccountRead) => void }) {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState<string | null>(null);
    const [busy, setBusy] = useState(false);

    async function submit(event: React.FormEvent) {
        event.preventDefault();
        setBusy(true);
        setError(null);
        try {
            onSignedIn(await askWorker<AccountRead>({ type: "signIn", email, password }));
        } catch (cause) {
            setError(cause instanceof Error ? cause.message : String(cause));
        } finally {
            setBusy(false);
        }
    }

    return (
        <form className="stack" onSubmit={submit}>
            <p className="muted">Sign in with your JobPilot account.</p>
            <input
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
            />
            <input
                type="password"
                placeholder="Password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
            />
            {error ? <p className="error">{error}</p> : null}
            <button type="submit" className="primary" disabled={busy}>
                {busy ? "Signing in…" : "Sign in"}
            </button>
        </form>
    );
}
