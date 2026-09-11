import path from "node:path";

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Stops `next dev` scaffolding AGENTS.md / CLAUDE.md when it detects an AI
  // coding agent in the environment. Without this it re-creates them on boot.
  agentRules: false,
  sassOptions: {
    // lets modules write `@use "@/style" as s`
    includePaths: [path.join(process.cwd(), "src")],
    silenceDeprecations: ["legacy-js-api"],
  },
};

export default nextConfig;
