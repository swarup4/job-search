import { configureStore } from "@reduxjs/toolkit";

import profile from "./profile/profileSlice";
import shell from "./shell/shellSlice";

/**
 * A factory, not a singleton. A module-level store is shared between requests on
 * the server, which leaks one user's data into another's render — the reason the
 * provider builds its own per client.
 */
export function makeStore() {
    return configureStore({ reducer: { profile, shell } });
}
