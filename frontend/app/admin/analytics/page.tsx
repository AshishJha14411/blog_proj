"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import PageHeader from "@/components/ui/PageHeader";
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
    <main className="mx-auto max-w-6xl space-y-8 px-6 py-14">
      <PageHeader
        eyebrow="Admin"
        title="Analytics"
        description={`Platform activity over the last ${days} days.`}
        actions={
          <div className="flex gap-1 rounded-full border border-border-soft bg-surface p-1">
            {RANGES.map((r) => (
              <button
                key={r}
                onClick={() => setDays(r)}
                className={`rounded-full px-3.5 py-1.5 text-sm font-medium transition-colors ${
                  days === r
                    ? "bg-primary text-on-primary"
                    : "text-text-light hover:bg-surface-muted hover:text-text"
                }`}
              >
                {r}d
              </button>
            ))}
          </div>
        }
      />

      {error ? (
        <div className="rounded-2xl border border-red-500/25 bg-red-500/10 p-4 text-sm text-red-600 dark:text-red-300">
          Couldn&apos;t load analytics: {(error as Error).message}
        </div>
      ) : null}

      {/* Clicks were fetched and totalled but never rendered — the sixth tile
          is that number finally reaching the page. */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-6">
        <StatCard label="Stories" value={totals.posts} loading={isLoading} />
        <StatCard label="New Users" value={totals.users} loading={isLoading} />
        <StatCard label="Ad Clicks" value={totals.clicks} loading={clicks.isLoading} />
        <StatCard label="Flags" value={totals.flags} loading={isLoading} />
        <StatCard label="AI Flags" value={totals.aiFlags} loading={isLoading} accent="amber" />
        <StatCard label="Human Flags" value={totals.humanFlags} loading={isLoading} />
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <ChartCard title="Stories per day" rows={posts.data} loading={posts.isLoading} />
        <ChartCard title="Signups per day" rows={users.data} loading={users.isLoading} />
      </div>

      <section>
        <h2 className="mb-4 font-display text-xl font-bold text-text">Recent moderation activity</h2>
        {logs.isLoading ? (
          <div className="skeleton h-32 rounded-2xl" />
        ) : (logs.data?.length ?? 0) === 0 ? (
          <p className="rounded-2xl border border-dashed border-border-strong p-8 text-center text-sm text-text-subtle">
            No moderation actions recorded yet.
          </p>
        ) : (
          <div className="overflow-x-auto rounded-2xl border border-border-soft bg-surface shadow-soft">
            <table className="w-full text-sm">
              <thead className="bg-surface-muted text-left text-xs uppercase tracking-wider text-text-subtle">
                <tr>
                  <th className="p-3 font-semibold">When</th>
                  <th className="p-3 font-semibold">Action</th>
                  <th className="p-3 font-semibold">Target</th>
                </tr>
              </thead>
              <tbody>
                {logs.data!.map((l) => (
                  <tr key={l.id} className="border-t border-border-soft">
                    <td className="p-3 whitespace-nowrap text-text-subtle">
                      {new Date(l.timestamp).toLocaleString()}
                    </td>
                    <td className="p-3 font-medium text-text">{l.action}</td>
                    <td className="p-3 text-text-light">
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
    <div className="rounded-2xl border border-border-soft bg-surface p-4 shadow-soft transition-colors hover:border-primary/30">
      <div className="text-xs font-medium uppercase tracking-wider text-text-subtle">{label}</div>
      <div
        className={`mt-2 font-display text-3xl font-bold ${
          accent === "amber" ? "text-amber-600 dark:text-amber-400" : "text-text"
        }`}
      >
        {loading ? <span className="text-text-subtle/40">—</span> : value}
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
    <section className="rounded-2xl border border-border-soft bg-surface p-5 shadow-soft">
      <div className="mb-4 flex items-baseline justify-between">
        <h2 className="font-semibold text-text">{title}</h2>
        <span className="text-sm text-text-subtle">{total} total</span>
      </div>

      {loading ? (
        <div className="skeleton h-32" />
      ) : total === 0 ? (
        <p className="flex h-32 items-center justify-center text-sm text-text-subtle">
          Nothing in this period.
        </p>
      ) : (
        <>
          <div className="flex h-32 items-end gap-px" role="img" aria-label={title}>
            {data.map((r) => (
              <div
                key={r.day}
                title={`${r.day}: ${r.count}`}
                className="flex-1 rounded-t bg-primary/70 transition-colors hover:bg-primary"
                // A zero-count day still gets a hairline so the axis reads as
                // continuous rather than looking like missing data.
                style={{ height: `${r.count === 0 ? 1 : (r.count / max) * 100}%` }}
              />
            ))}
          </div>
          <div className="mt-2 flex justify-between text-xs text-text-subtle">
            <span>{data[0]?.day}</span>
            <span>{data[data.length - 1]?.day}</span>
          </div>
        </>
      )}
    </section>
  );
}
