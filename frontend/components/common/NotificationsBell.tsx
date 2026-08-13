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
        className="relative inline-flex h-9 w-9 items-center justify-center rounded-full border border-white/10 bg-white/5 text-on-dark/80 transition-colors hover:border-primary/40 hover:bg-white/10 hover:text-primary"
        aria-label="Notifications"
        aria-expanded={open}
      >
        <svg
          aria-hidden="true"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth={1.7}
          strokeLinecap="round"
          strokeLinejoin="round"
          className="h-[18px] w-[18px]"
        >
          <path d="M18 8a6 6 0 1 0-12 0c0 6-2 7-2 7h16s-2-1-2-7" />
          <path d="M13.7 20a2 2 0 0 1-3.4 0" />
        </svg>
        {unread > 0 && (
          <span className="absolute -top-0.5 -right-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-primary px-1 text-[10px] font-bold text-on-primary ring-2 ring-[var(--nav-background)]">
            {unread}
          </span>
        )}
      </button>

      {open && (
        <div className="rise-in absolute right-0 z-50 mt-3 w-80 overflow-hidden rounded-2xl border border-border-soft bg-surface shadow-lift">
          <div className="flex items-center justify-between border-b border-border-soft px-4 py-3">
            <div className="text-sm font-semibold text-text">Notifications</div>
            <button
              className="text-xs font-medium text-primary-strong transition-colors hover:underline"
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
            <div className="space-y-2 p-4">
              <div className="skeleton h-3 w-2/3" />
              <div className="skeleton h-3 w-1/2" />
            </div>
          ) : items.length === 0 ? (
            <div className="px-4 py-8 text-center text-sm text-text-subtle">
              You&apos;re all caught up.
            </div>
          ) : (
            <ul className="max-h-96 overflow-y-auto">
              {items.map((n) => (
                <li
                  key={n.id}
                  className="cursor-pointer border-b border-border-soft px-4 py-3 transition-colors last:border-b-0 hover:bg-primary/8"
                  onClick={() => onClickItem(n)}
                >
                  <div className="flex items-start gap-2.5">
                    {/* Unread marker: a rose dot instead of a colour-only cue
                        buried in the text weight. */}
                    <span
                      aria-hidden="true"
                      className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${
                        !n.is_read ? 'bg-primary' : 'bg-transparent'
                      }`}
                    />
                    <div className="min-w-0 flex-1">
                      <div className="text-sm capitalize">
                        <span className={!n.is_read ? "font-semibold text-text" : "text-text-light"}>
                          {(n.action ?? "").replaceAll("_", " ")}
                        </span>
                      </div>
                      <div className="mt-0.5 text-xs text-text-subtle">
                        {new Date(n.created_at).toLocaleString()}
                      </div>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}

          <div className="border-t border-border-soft px-4 py-2.5 text-right">
            <Link
              href="/notifications"
              className="text-xs font-medium text-primary-strong transition-colors hover:underline"
            >
              View all
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
