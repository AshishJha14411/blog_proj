"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import {
  getClicksDaily,
  getFlagsBreakdown,
  getModerationLogs,
  getPostsDaily,
  getUsersDaily,
  type DayCount,
} from "@/services/analyticsService";
import { useModGuard } from "@/hooks/useModGuard";

const RANGES = [7, 30, 90] as const;

export default function AdminAnalyticsPage() {
  const { isMod } = useModGuard();
  const [days, setDays] = useState<number>(30);

  // WHY TanStack rather than useEffect + .then(setState): the previous version
  // dropped every rejection on the floor, so a 404 rendered as a page full of
  // zeros that looked like "no data" instead of "the request failed". Query
  // gives us the error object, and the UI below actually surfaces it.
  const posts = useQuery({ queryKey: ["analytics", "posts", days], queryFn: () => getPostsDaily(days), enabled: isMod });
  const users = useQuery({ queryKey: ["analytics", "users", days], queryFn: () => getUsersDaily(days), enabled: isMod });
  const clicks = useQuery({ queryKey: ["analytics", "clicks", days], queryFn: () => getClicksDaily(days), enabled: isMod });
  const flags = useQuery({ queryKey: ["analytics", "flags"], queryFn: getFlagsBreakdown, enabled: isMod });
  const logs = useQuery({ queryKey: ["analytics", "moderation"], queryFn: () => getModerationLogs(25), enabled: isMod });

  const sum = (rows?: DayCount[]) => (rows ?? []).reduce((a, r) => a + r.count, 0);

  const totals = useMemo(
    () => ({
      posts: sum(posts.data),
      users: sum(users.data),
      clicks: sum(clicks.data),
      flags: flags.data?.total ?? 0,
      aiFlags: flags.data?.ai_flags ?? 0,
      humanFlags: flags.data?.human_flags ?? 0,
    }),
    [posts.data, users.data, clicks.data, flags.data]
  );

  const isLoading = posts.isLoading || users.isLoading || flags.isLoading;
  const error = posts.error || users.error || clicks.error || flags.error;

  if (!isMod) return null;

  return (
    <main className="mx-auto max-w-6xl p-6 space-y-8">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Analytics</h1>
          <p className="text-sm text-gray-500">Platform activity over the last {days} days.</p>
        </div>
        <div className="flex gap-1 rounded-lg border p-1">
          {RANGES.map((r) => (
            <button
              key={r}
              onClick={() => setDays(r)}
              className={`rounded-md px-3 py-1.5 text-sm transition ${
                days === r ? "bg-gray-900 text-white" : "text-gray-600 hover:bg-gray-100"
              }`}
            >
              {r}d
            </button>
          ))}
        </div>
      </header>

      {error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          Couldn&apos;t load analytics: {(error as Error).message}
        </div>
      ) : null}

      <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
        <StatCard label="Stories" value={totals.posts} loading={isLoading} />
        <StatCard label="New Users" value={totals.users} loading={isLoading} />
        <StatCard label="Flags" value={totals.flags} loading={isLoading} />
        <StatCard label="AI Flags" value={totals.aiFlags} loading={isLoading} accent="amber" />
        <StatCard label="Human Flags" value={totals.humanFlags} loading={isLoading} />
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <ChartCard title="Stories per day" rows={posts.data} loading={posts.isLoading} />
        <ChartCard title="Signups per day" rows={users.data} loading={users.isLoading} />
      </div>

      <section>
        <h2 className="mb-2 font-medium">Recent moderation activity</h2>
        {logs.isLoading ? (
          <p className="text-sm text-gray-500">Loading…</p>
        ) : (logs.data?.length ?? 0) === 0 ? (
          <p className="rounded-lg border border-dashed p-6 text-center text-sm text-gray-500">
            No moderation actions recorded yet.
          </p>
        ) : (
          <div className="overflow-x-auto rounded-lg border">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="p-2 text-left">When</th>
                  <th className="p-2 text-left">Action</th>
                  <th className="p-2 text-left">Target</th>
                </tr>
              </thead>
              <tbody>
                {logs.data!.map((l) => (
                  <tr key={l.id} className="border-t">
                    <td className="p-2 whitespace-nowrap text-gray-600">
                      {new Date(l.timestamp).toLocaleString()}
                    </td>
                    <td className="p-2 font-medium">{l.action}</td>
                    <td className="p-2 text-gray-600">
                      {l.target_type ? `${l.target_type} ${String(l.target_id ?? "").slice(0, 8)}` : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}

function StatCard({
  label,
  value,
  loading,
  accent,
}: {
  label: string;
  value: number;
  loading?: boolean;
  accent?: "amber";
}) {
  return (
    <div className="rounded-lg border bg-white p-3">
      <div className="text-xs text-gray-500">{label}</div>
      <div className={`text-2xl font-semibold ${accent === "amber" ? "text-amber-600" : ""}`}>
        {loading ? <span className="text-gray-300">—</span> : value}
      </div>
    </div>
  );
}

/**
 * Dependency-free bar chart. A charting library would be a lot of bundle for
 * two small series, and the data is already zero-filled per day by the backend
 * so the bars line up with the axis without any client-side gap filling.
 */
function ChartCard({
  title,
  rows,
  loading,
}: {
  title: string;
  rows?: DayCount[];
  loading?: boolean;
}) {
  const data = rows ?? [];
  const max = Math.max(1, ...data.map((r) => r.count));
  const total = data.reduce((a, r) => a + r.count, 0);

  return (
    <section className="rounded-lg border bg-white p-4">
      <div className="mb-3 flex items-baseline justify-between">
        <h2 className="font-medium">{title}</h2>
        <span className="text-sm text-gray-500">{total} total</span>
      </div>

      {loading ? (
        <div className="h-32 animate-pulse rounded bg-gray-100" />
      ) : total === 0 ? (
        <p className="flex h-32 items-center justify-center text-sm text-gray-500">
          Nothing in this period.
        </p>
      ) : (
        <>
          <div className="flex h-32 items-end gap-px" role="img" aria-label={title}>
            {data.map((r) => (
              <div
                key={r.day}
                title={`${r.day}: ${r.count}`}
                className="flex-1 rounded-t bg-gray-900/80 transition hover:bg-gray-900"
                // A zero-count day still gets a hairline so the axis reads as
                // continuous rather than looking like missing data.
                style={{ height: `${r.count === 0 ? 1 : (r.count / max) * 100}%` }}
              />
            ))}
          </div>
          <div className="mt-2 flex justify-between text-xs text-gray-500">
            <span>{data[0]?.day}</span>
            <span>{data[data.length - 1]?.day}</span>
          </div>
        </>
      )}
    </section>
  );
}
