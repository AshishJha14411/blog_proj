"use client";

import { useEffect, useState } from "react";
import { fetchModQueue, ModQueueParams, QueueItem } from "@/services/moderationService";
import Link from "next/link";
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

  return (
    <main className="mx-auto max-w-5xl p-6">
      <h1 className="text-2xl font-semibold mb-4">Moderation Queue</h1>

      <div className="flex gap-2 mb-4">
        <select
          value={params.status || "flagged"}
          onChange={(e) => setParams((s) => ({ ...s, status: e.target.value as any, offset: 0 }))}
          className="border rounded p-2"
        >
          <option value="flagged">Flagged</option>
          <option value="generated">Generated</option>
          <option value="rejected">Rejected</option>
          <option value="">All</option>
        </select>
        {/* add author/tag inputs later if you like */}
      </div>

      {loading ? (
        <div>Loading…</div>
      ) : items.length === 0 ? (
        <div className="text-gray-500">Nothing to review 🎉</div>
      ) : (
        <table className="w-full text-sm border">
          <thead className="bg-gray-50">
            <tr>
              <th className="p-2 text-left">Title</th>
              <th className="p-2">Author</th>
              <th className="p-2">Status</th>
              <th className="p-2">Flags</th>
              <th className="p-2">Created</th>
              <th className="p-2"></th>
            </tr>
          </thead>
          <tbody>
            {items.map((it) => (
              <tr key={it.id} className="border-t">
                <td className="p-2">{it.title}</td>
                <td className="p-2 text-center">{it.user?.username}</td>
                <td className="p-2 text-center">{it.is_flagged ? "flagged" : (it.status || "—")}</td>
                <td className="p-2 text-center">{it.flag_count ?? 0}</td>
                <td className="p-2 text-center">{new Date(it.created_at).toLocaleDateString()}</td>
                <td className="p-2 text-right">
                  <Link href={`/admin/mod/posts/${it.id}`} className="underline">Review</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {/* simple pager */}
      <div className="mt-4 flex justify-between">
        <button
          className="rounded border px-3 py-1"
          disabled={(params.offset || 0) === 0}
          onClick={() => setParams((s) => ({ ...s, offset: Math.max(0, (s.offset || 0) - (s.limit || 10)) }))}
        >
          Prev
        </button>
        <div>Showing {(params.offset || 0) + 1}-{Math.min((params.offset || 0) + (params.limit || 10), total)} of {total}</div>
        <button
          className="rounded border px-3 py-1"
          disabled={(params.offset || 0) + (params.limit || 10) >= total}
          onClick={() => setParams((s) => ({ ...s, offset: (s.offset || 0) + (s.limit || 10) }))}
        >
          Next
        </button>
      </div>
    </main>
  );
}
