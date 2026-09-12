"use client";

import { useEffect, useRef } from "react";
import { Provider } from "react-redux";

import { sessionRestored } from "./auth/authSlice";
import { makeStore } from "./store";

/** Built once per client and kept across navigations; never rebuilt on re-render. */
export function StoreProvider({ children }) {
    const storeRef = useRef(null);
    if (!storeRef.current) storeRef.current = makeStore();

    // In an effect, not during render: sessionStorage does not exist on the server,
    // and reading it while rendering would make the server and the client disagree.
    useEffect(() => {
        storeRef.current.dispatch(sessionRestored());
    }, []);

    return <Provider store={storeRef.current}>{children}</Provider>;
}
