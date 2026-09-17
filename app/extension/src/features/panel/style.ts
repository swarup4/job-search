/** Shared with `index.ts`, which reserves exactly this much page width. */
export const PANEL_WIDTH = 380;

/** Lives in a shadow root, so these names cannot collide with the page's own and
 * the page's stylesheet cannot reach in. */
export const PANEL_CSS = `
:host { all: initial; }
* { box-sizing: border-box; }

.panel {
    position: fixed;
    top: 0;
    right: 0;
    bottom: 0;
    width: ${PANEL_WIDTH}px;
    /* Above the ATS's own chrome. Workday's sticky header and its submit bar
       both claim high z-indexes and would otherwise paint over the panel. */
    z-index: 2147483647;
    display: flex;
    flex-direction: column;
    border-left: 1px solid #1e293b;
    background: #0f172a;
    color: #e2e8f0;
    font: 13px/1.5 ui-sans-serif, system-ui, -apple-system, sans-serif;
    box-shadow: -8px 0 24px rgba(2, 6, 23, 0.25);
    overflow: hidden;
}

header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 14px;
    border-bottom: 1px solid #1e293b;
}

header .title { font-weight: 600; }
header .title span { color: #64748b; font-weight: 400; }

button {
    border: 1px solid #334155;
    border-radius: 7px;
    background: #1e293b;
    color: #e2e8f0;
    font: inherit;
    padding: 7px 10px;
    cursor: pointer;
}
button:hover { border-color: #475569; }
button:disabled { opacity: 0.5; cursor: default; }

button.icon {
    border: 0;
    background: none;
    color: #94a3b8;
    font-size: 18px;
    line-height: 1;
    padding: 2px 6px;
}

button.confirm {
    border-color: #22c55e;
    color: #4ade80;
}

button.primary {
    width: 100%;
    border-color: transparent;
    background: #22c55e;
    color: #05230f;
    font-weight: 600;
}

.body {
    flex: 1;
    overflow-y: auto;
    padding: 12px 14px;
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.counts { display: flex; flex-wrap: wrap; gap: 6px; }

.tag {
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 600;
}
.tag.good { background: rgba(34, 197, 94, 0.15); color: #4ade80; }
.tag.warn { background: rgba(245, 158, 11, 0.15); color: #fbbf24; }
.tag.plain { background: rgba(148, 163, 184, 0.15); color: #94a3b8; }

h2 {
    margin: 0 0 8px;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: #94a3b8;
}

.hint {
    margin: 0;
    padding: 9px 11px;
    border-radius: 8px;
    background: #1e293b;
    color: #94a3b8;
}

ol, ul { margin: 0; padding: 0; list-style: none; }

.questions li { margin-bottom: 12px; }

.questions label {
    display: block;
    margin-bottom: 4px;
    color: #cbd5e1;
    cursor: pointer;
}
.questions label:hover { color: #e2e8f0; text-decoration: underline; }

.questions .ats {
    display: block;
    font-size: 11px;
    color: #64748b;
    text-transform: none;
}

input, select, textarea {
    width: 100%;
    padding: 7px 9px;
    border: 1px solid #334155;
    border-radius: 7px;
    background: #1e293b;
    color: #e2e8f0;
    font: inherit;
}
input:focus, select:focus, textarea:focus { outline: 2px solid #22c55e; outline-offset: 0; }

textarea { resize: vertical; min-height: 64px; }

details summary {
    cursor: pointer;
    color: #94a3b8;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

.fills li {
    display: flex;
    justify-content: space-between;
    gap: 10px;
    padding: 6px 0;
    border-bottom: 1px solid #1e293b;
}
.fills li:last-child { border-bottom: 0; }
.fills .label { color: #94a3b8; }
.fills .value { color: #e2e8f0; text-align: right; overflow-wrap: anywhere; }

footer {
    padding: 10px 14px;
    border-top: 1px solid #1e293b;
    display: flex;
    gap: 8px;
}
footer button { flex: 1; }
.note {
    padding: 0 14px 10px;
    color: #64748b;
    font-size: 11px;
}
`;
