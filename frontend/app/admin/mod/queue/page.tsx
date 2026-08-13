"use client";

import { useEffect, useState } from "react";
import { fetchModQueue, ModQueueParams, QueueItem } from "@/services/moderationService";
import Link from "next/link";
import Badge from "@/components/ui/Badge";
import PageHeader from "@/components/ui/PageHeader";
import Select from "@/components/ui/Select";
import { useModGuard } from "@/hooks/useModGuard";

export default function ModQueuePage() {
  const { ready, isMod } = useModGuard();
  const [items, setItems] = useState<QueueItem[]>([]);
  const [total, setTotal] = useState(0);
  const [params, setParams] = useState<ModQueueParams>({ status: "flagged", limit: 10, offset: 0 });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!ready || !isMod) return;
    setLoading(true);
    fetchModQueue(params)
      .then((d) => { setItems(d.items); setTotal(d.total); })
      .finally(() => setLoading(false));
  }, [params, ready, isMod]);

  if (!isMod) return null;

  const pagerButton =
    'rounded-full border border-border-soft bg-surface px-4 py-2 text-sm font-medium text-text transition-colors hover:border-primary/40 hover:text-primary-strong disabled:cursor-not-allowed disabled:opacity-45';

  return (
    <main className="mx-auto max-w-5xl px-6 py-14">
      <PageHeader
        eyebrow="Admin"
        title="Moderation Queue"
        description={`${total} ${total === 1 ? 'item' : 'items'} matching this filter.`}
        actions={
          <Select
            value={params.status || "flagged"}
            onChange={(e) => setParams((s) => ({ ...s, status: e.target.value as ModQueueParams['status'], offset: 0 }))}
            className="mt-0 w-44"
            aria-label="Filter by status"
          >
            <option value="flagged">Flagged</option>
            <option value="generated">Generated</option>
            <option value="rejected">Rejected</option>
            <option value="">All</option>
          </Select>
        }
      />

      {loading ? (
        <div className="skeleton h-56 rounded-2xl" />
      ) : items.length === 0 ? (
        <p className="rounded-2xl border border-dashed border-border-strong p-10 text-center text-sm text-text-subtle">
          Nothing to review 🎉
        </p>
      ) : (
        <div className="overflow-x-auto rounded-2xl border border-border-soft bg-surface shadow-soft">
          <table className="w-full text-sm">
            <thead className="bg-surface-muted text-left text-xs uppercase tracking-wider text-text-subtle">
              <tr>
                <th className="p-3 font-semibold">Title</th>
                <th className="p-3 font-semibold">Author</th>
                <th className="p-3 font-semibold">Status</th>
                <th className="p-3 font-semibold">Flags</th>
                <th className="p-3 font-semibold">Created</th>
                <th className="p-3"></th>
              </tr>
            </thead>
            <tbody>
              {items.map((it) => (
                <tr key={it.id} className="border-t border-border-soft transition-colors hover:bg-primary/5">
                  <td className="p-3 font-medium text-text">{it.title}</td>
                  <td className="p-3 text-text-light">{it.user?.username}</td>
                  <td className="p-3">
                    {it.is_flagged ? (
                      <Badge tone="warning" dot>flagged</Badge>
                    ) : (
                      <Badge tone="neutral">{it.status || "—"}</Badge>
                    )}
                  </td>
                  <td className="p-3 text-text-light">{it.flag_count ?? 0}</td>
                  <td className="p-3 whitespace-nowrap text-text-subtle">
                    {new Date(it.created_at).toLocaleDateString()}
                  </td>
                  <td className="p-3 text-right">
                    <Link
                      href={`/admin/mod/posts/${it.id}`}
                      className="font-medium text-primary-strong hover:underline"
                    >
                      Review
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* simple pager */}
      <div className="mt-8 flex items-center justify-between gap-4">
        <button
          className={pagerButton}
          disabled={(params.offset || 0) === 0}
          onClick={() => setParams((s) => ({ ...s, offset: Math.max(0, (s.offset || 0) - (s.limit || 10)) }))}
        >
          ← Prev
        </button>
        <div className="text-sm text-text-subtle">
          Showing {(params.offset || 0) + 1}-{Math.min((params.offset || 0) + (params.limit || 10), total)} of {total}
        </div>
        <button
          className={pagerButton}
          disabled={(params.offset || 0) + (params.limit || 10) >= total}
          onClick={() => setParams((s) => ({ ...s, offset: (s.offset || 0) + (s.limit || 10) }))}
        >
          Next →
        </button>
      </div>
    </main>
  );
}
