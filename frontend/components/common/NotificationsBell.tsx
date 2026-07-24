"use client";
/**
 * WHY: previously the bell polled every 5 minutes for an unread count.
 * Phase 3 pushes changes over WebSocket instead, and the bell falls back
 * to the polling hook if the socket downgrades.
 */
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";

import { useNotificationSocket } from "@/hooks/useNotificationSocket";
import { useUnreadNotifications } from "@/hooks/useUnreadNotifications";
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
  const [socketUnread, setSocketUnread] = useState(0);

  // WHY: the socket handles updates in real time. If it downgrades (too
  // many failed reconnects) we fall through to polling — the hook returns
  // 0 downgraded=false when everything is fine.
  const socket = useNotificationSocket(
    useCallback((msg) => {
      if (msg.type !== "notification") return;
      // Optimistically bump the badge. When the dropdown opens we'll
      // reconcile against the server's list.
      setSocketUnread((n) => n + 1);
    }, []),
  );

  // WHY: only run the polling hook when the socket downgraded. If the
  // socket is alive, polling is redundant and wastes a request every 5 min.
  const polled = useUnreadNotifications(socket.downgraded ? 300_000 : 60 * 60 * 1000);
  const unread = socket.downgraded ? polled : socketUnread + polled;

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    getNotifications(false, 10, 0)
      .then((d) => {
        setItems(d.items);
        // WHY: reconcile the optimistic counter against reality once we
        // have the authoritative list.
        setSocketUnread(0);
      })
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, [open]);

  async function onClickItem(n: NotificationItem) {
    setItems((prev) =>
      prev.map((x) => (x.id === n.id ? { ...x, is_read: true } : x)),
    );
    try {
      await markRead(n.id);
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
    <div className="relative">
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
                setSocketUnread(0);
                try {
                  await markAllRead();
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
