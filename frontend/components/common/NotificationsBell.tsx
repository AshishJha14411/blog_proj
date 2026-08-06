"use client";
/**
 * WHY: previously the bell polled every 5 minutes for an unread count.
 * Phase 3 pushes changes over WebSocket instead, and the bell falls back
 * to the polling hook if the socket downgrades.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useQueryClient } from "@tanstack/react-query";

import { useNotificationSocket } from "@/hooks/useNotificationSocket";
import { unreadCountKey, useUnreadNotifications } from "@/hooks/useUnreadNotifications";
import {
  getNotifications,
  markAllRead,
  markRead,
  NotificationItem,
} from "@/services/notificationService";

export default function NotificationsBell() {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(false);
  const queryClient = useQueryClient();
  const rootRef = useRef<HTMLDivElement>(null);

  // Marking things read changes server state the badge is derived from, so
  // invalidate rather than waiting for the next poll (which can be an hour away
  // while the socket is healthy). This also keeps the bell in step with the
  // /notifications page, which invalidates the same key.
  const refreshUnread = useCallback(() => {
    void queryClient.invalidateQueries({ queryKey: ["notifications"] });
  }, [queryClient]);

  // WHY: a dropdown that only closes via its own trigger feels broken — clicking
  // anywhere else on the page should dismiss it, and Escape should too. Listens
  // on `mousedown` so the menu closes before a click lands on whatever is
  // underneath it.
  useEffect(() => {
    if (!open) return;
    function onPointerDown(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  // WHY: the socket handles updates in real time. If it downgrades (too
  // many failed reconnects) we fall through to polling — the hook returns
  // 0 downgraded=false when everything is fine.
  //
  // WHY invalidate instead of keeping a counter: the arriving notification is
  // already persisted, so the server's unread count includes it. Adding a local
  // tally on top (`socketUnread + polled`) counted the same notification twice
  // as soon as the count refetched. Invalidating makes the server the single
  // source of truth and keeps the badge correct across tabs.
  const socket = useNotificationSocket(
    useCallback((msg) => {
      if (msg.type !== "notification") return;
      void queryClient.invalidateQueries({ queryKey: unreadCountKey });
    }, [queryClient]),
  );

  // WHY: only run the polling hook when the socket downgraded. If the
  // socket is alive, polling is redundant and wastes a request every 5 min.
  const unread = useUnreadNotifications(socket.downgraded ? 300_000 : 60 * 60 * 1000);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    getNotifications(false, 10, 0)
      .then((d) => {
        setItems(d.items);
        // The list we just fetched is authoritative; make sure the badge
        // reflects the same server state rather than an older cached count.
        refreshUnread();
      })
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, [open, refreshUnread]);

  async function onClickItem(n: NotificationItem) {
    setItems((prev) =>
      prev.map((x) => (x.id === n.id ? { ...x, is_read: true } : x)),
    );
    try {
      await markRead(n.id);
      refreshUnread(); // badge must drop immediately, not on the next poll
    } catch {
      // best-effort; UI already reflects the intent
    }

    const href =
      n.target_type === "story"
        ? `/stories/${n.target_id}`
        : n.target_type === "comment"
          ? `/stories/${n.target_id}`
          : "/notifications";
    window.location.href = href;
  }

  return (
    <div className="relative" ref={rootRef}>
      <button
        onClick={() => setOpen((s) => !s)}
        className="relative rounded p-2 hover:bg-gray-100"
        aria-label="Notifications"
      >
        🔔
        {unread > 0 && (
          <span className="absolute -top-1 -right-1 rounded-full bg-red-500 text-white text-xs px-1">
            {unread}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-80 rounded border bg-white shadow z-50">
          <div className="flex items-center justify-between p-2 border-b">
            <div className="font-medium">Notifications</div>
            <button
              className="text-xs underline"
              onClick={async () => {
                setItems((prev) => prev.map((x) => ({ ...x, is_read: true })));
                try {
                  await markAllRead();
                  refreshUnread(); // was leaving a stale number on the bell
                } catch {
                  // ignore — reload will resync
                }
              }}
            >
              Mark all read
            </button>
          </div>

          {loading ? (
            <div className="p-3 text-sm text-gray-500">Loading…</div>
          ) : items.length === 0 ? (
            <div className="p-3 text-sm text-gray-500">You&apos;re all caught up.</div>
          ) : (
            <ul className="max-h-96 overflow-y-auto">
              {items.map((n) => (
                <li
                  key={n.id}
                  className="p-3 border-b hover:bg-gray-50 cursor-pointer"
                  onClick={() => onClickItem(n)}
                >
                  <div className="text-sm">
                    <span className={!n.is_read ? "font-semibold" : ""}>
                      {(n.action ?? "").replaceAll("_", " ")}
                    </span>
                  </div>
                  <div className="text-xs text-gray-500">
                    {new Date(n.created_at).toLocaleString()}
                  </div>
                </li>
              ))}
            </ul>
          )}

          <div className="p-2 text-right">
            <Link href="/notifications" className="text-xs underline">
              View all
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
