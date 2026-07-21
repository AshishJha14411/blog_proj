import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Compile errors and lint failures must not ship to production.
  // Run `npm run build` locally after pulling to surface any remaining issues.
  eslint: {
    ignoreDuringBuilds: false,
  },
  typescript: {
    ignoreBuildErrors: false,
  },

  // Ensure your environment variable for the backend is respected
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
  },
};

export default nextConfig;
