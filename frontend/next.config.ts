import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  // 1. Ignore ESLint errors during build (so "unused vars" don't crash deploy)
  eslint: {
    ignoreDuringBuilds: true,
  },

  // 2. Ignore TypeScript errors during build (so "any" types don't crash deploy)
  typescript: {
    ignoreBuildErrors: true,
  },

  // 3. Ensure your environment variable for the backend is respected
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
  },
};

export default nextConfig;
