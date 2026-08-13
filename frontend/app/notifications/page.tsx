"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import EmptyState from "@/components/ui/EmptyState";
import PageHeader from "@/components/ui/PageHeader";
import { markRead } from "@/services/notificationService";
import { useNotifications } from "@/hooks/queries";

export default function NotificationsPage() {
  const limit = 20;
  const [offset, setOffset] = useState(0);
  const queryClient = useQueryClient();

  // TanStack owns the fetch: no useEffect, no manual loading/error/cancelled
  // flags, no stale-response races. Changing `offset` changes the query key,
  // which refetches (and caches) automatically.
  const { data, isError } = useNotifications(false, limit, offset);
  const items = data?.items ?? [];
  const total = data?.total ?? 0;

  // Mutation + invalidation replaces the old hand-rolled `load()` re-fetch:
  // marking one read invalidates the notifications cache, which refetches.
  const markReadMutation = useMutation({
    mutationFn: (id: string) => markRead(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notifications"] }),
  });

  const pagerButton =
    'rounded-full border border-border-soft bg-surface px-4 py-2 text-sm font-medium text-text transition-colors hover:border-primary/40 hover:text-primary-strong disabled:cursor-not-allowed disabled:opacity-45';

  return (
    <main className="mx-auto max-w-3xl px-6 py-14">
      <PageHeader eyebrow="Activity" title="Notifications" />

      {isError && (
        <div className="mb-4 rounded-2xl border border-red-500/25 bg-red-500/10 px-4 py-3 text-sm text-red-600 dark:text-red-300">
          Couldn&apos;t load notifications. Please try again in a moment.
        </div>
      )}

      {items.length === 0 ? (
        <EmptyState
          title="Nothing new"
          description="Likes, comments and moderation updates on your stories show up here."
        />
      ) : (
        <ul className="space-y-3">
          {items.map((n) => (
            <li
              key={n.id}
              className={`flex items-start gap-3 rounded-2xl border bg-surface px-4 py-3.5 shadow-soft transition-colors ${
                n.is_read ? 'border-border-soft' : 'border-primary/30'
              }`}
            >
              <span
                aria-hidden="true"
                className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${
                  n.is_read ? 'bg-border-strong' : 'bg-primary'
                }`}
              />
              <div className="min-w-0 flex-1">
                {/* F11: guard against server sending a null action */}
                <div className={`capitalize ${n.is_read ? 'text-text-light' : 'font-medium text-text'}`}>
                  {(n.action ?? "").replaceAll("_", " ")}
                </div>
                <div className="mt-1 text-xs text-text-subtle">
                  {new Date(n.created_at).toLocaleString()}
                </div>
              </div>
              {!n.is_read && (
                <button
                  className="shrink-0 rounded-full px-3 py-1 text-xs font-medium text-primary-strong transition-colors hover:bg-primary/10 disabled:opacity-50"
                  disabled={markReadMutation.isPending}
                  onClick={() => markReadMutation.mutate(n.id)}
                >
                  Mark read
                </button>
              )}
            </li>
          ))}
        </ul>
      )}

      {total > 0 && (
        <div className="mt-8 flex items-center justify-between gap-4">
          <button
            className={pagerButton}
            disabled={offset === 0}
            onClick={() => setOffset(Math.max(0, offset - limit))}
          >
            ← Prev
          </button>
          <div className="text-sm text-text-subtle">
            Showing {total === 0 ? 0 : offset + 1}-{Math.min(offset + limit, total)} of {total}
          </div>
          <button
            className={pagerButton}
            disabled={offset + limit >= total}
            onClick={() => setOffset(offset + limit)}
          >
            Next →
          </button>
        </div>
      )}
    </main>
  );
}
