import { createRoot } from "react-dom/client";

import { App } from "@/popup/App";
import "@/popup/popup.css";

const host = document.getElementById("root");
if (host) createRoot(host).render(<App />);
