import path from "node:path";

/** @type {import('next').NextConfig} */
const nextConfig = {
  sassOptions: {
    // lets modules write `@use "@/style" as s`
    includePaths: [path.join(process.cwd(), "src")],
    silenceDeprecations: ["legacy-js-api"],
  },
};

export default nextConfig;
