"use client";

/**
 * App-wide client providers. Currently: TanStack Query.
 *
 * WHY TanStack Query: the app hand-rolls `fetch-in-useEffect` on every page,
 * each re-implementing loading/error/refetch state — the source of the race /
 * missing-cleanup / stale-response bugs from the audit. React Query makes
 * server state a first-class concept: caching, background refetch, dedup, and
 * invalidation, with those bug classes handled once, correctly.
 *
 * The QueryClient is created inside a useState initializer so it's stable
 * across renders but still per-request on the server (never shared between
 * users during SSR).
 */
import { useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

export default function Providers({ children }: { children: React.ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            // Data is fresh for 30s before a background refetch is considered.
            staleTime: 30_000,
            // The axios interceptor already handles 401->refresh; don't hammer
            // the API retrying genuine 4xx.
            retry: 1,
            refetchOnWindowFocus: false,
          },
        },
      }),
  );

  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
