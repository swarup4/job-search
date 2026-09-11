"use client";

import { useRef } from "react";
import { Provider } from "react-redux";

import { makeStore } from "./store";

/** Built once per client and kept across navigations; never rebuilt on re-render. */
export function StoreProvider({ children }) {
    const storeRef = useRef(null);
    if (!storeRef.current) storeRef.current = makeStore();

    return <Provider store={storeRef.current}>{children}</Provider>;
}
