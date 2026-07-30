"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

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

  return (
    <main className="mx-auto max-w-3xl p-6">
      <h1 className="text-2xl font-semibold mb-4">Notifications</h1>
      {isError && (
        <div className="mb-4 rounded border border-red-300 bg-red-50 p-2 text-sm text-red-700">
          Couldn&apos;t load notifications. Please try again in a moment.
        </div>
      )}
      {items.length === 0 ? (
        <div className="text-gray-500">No notifications.</div>
      ) : (
        <ul className="space-y-3">
          {items.map((n) => (
            <li key={n.id} className="border rounded p-3">
              <div className="flex justify-between">
                {/* F11: guard against server sending a null action */}
                <div className={!n.is_read ? "font-medium" : ""}>{(n.action ?? "").replaceAll("_", " ")}</div>
                {!n.is_read && (
                  <button
                    className="text-xs underline disabled:opacity-50"
                    disabled={markReadMutation.isPending}
                    onClick={() => markReadMutation.mutate(n.id)}
                  >
                    Mark read
                  </button>
                )}
              </div>
              <div className="text-xs text-gray-500 mt-1">{new Date(n.created_at).toLocaleString()}</div>
            </li>
          ))}
        </ul>
      )}

      <div className="mt-4 flex justify-between">
        <button className="rounded border px-3 py-1" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - limit))}>Prev</button>
        <div>Showing {total === 0 ? 0 : offset + 1}-{Math.min(offset + limit, total)} of {total}</div>
        <button className="rounded border px-3 py-1" disabled={offset + limit >= total} onClick={() => setOffset(offset + limit)}>Next</button>
      </div>
    </main>
  );
}
