import { context } from "esbuild";
import { cp, mkdir, readdir, readFile, rm } from "node:fs/promises";

const watch = process.argv.includes("--watch");
const OUT = "dist";

/** server/.env-style parse. No dotenv dependency for three lines of work. */
async function loadEnv() {
    try {
        const text = await readFile(".env", "utf8");
        for (const line of text.split("\n")) {
            const match = /^\s*([A-Z_][A-Z0-9_]*)\s*=\s*(.*?)\s*$/.exec(line);
            if (match) process.env[match[1]] ??= match[2].replace(/^["']|["']$/g, "");
        }
    } catch {
        // No .env is the normal case — the default below is the localhost API.
    }
}

await loadEnv();
// Empty the directory rather than replace it: Chrome holds an unpacked
// extension by its folder, and deleting that folder out from under a loaded
// extension leaves it serving a stale copy until it is removed and re-added.
await mkdir(OUT, { recursive: true });
for (const entry of await readdir(OUT)) {
    await rm(`${OUT}/${entry}`, { recursive: true, force: true });
}

const shared = {
    bundle: true,
    // MV3 forbids ESM in content scripts, and a classic worker keeps one format
    // across all three entrypoints.
    format: "iife",
    target: "chrome116",
    platform: "browser",
    minify: !watch,
    sourcemap: watch ? "inline" : false,
    legalComments: "none",
    logLevel: "info",
    define: {
        "process.env.NODE_ENV": JSON.stringify(watch ? "development" : "production"),
        __API_URL__: JSON.stringify(process.env.JOBPILOT_API_URL ?? "http://127.0.0.1:8000/api"),
    },
};

const builds = [
    { ...shared, entryPoints: ["src/background.ts"], outfile: `${OUT}/background.js` },
    { ...shared, entryPoints: ["src/content.ts"], outfile: `${OUT}/content.js` },
    { ...shared, entryPoints: ["src/popup/index.tsx"], outfile: `${OUT}/popup.js` },
];

const contexts = await Promise.all(builds.map(context));

async function copyStatic() {
    await cp("public", OUT, { recursive: true });
}

if (watch) {
    await copyStatic();
    await Promise.all(contexts.map((ctx) => ctx.watch()));
    console.log(`watching — load ${OUT}/ unpacked at chrome://extensions`);
} else {
    await Promise.all(contexts.map((ctx) => ctx.rebuild()));
    await copyStatic();
    await Promise.all(contexts.map((ctx) => ctx.dispose()));
    console.log(`built ${OUT}/`);
}
