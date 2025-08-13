"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getNotifications, markAllRead, markRead, NotificationItem } from "@/services/notificationService";
import { useUnreadNotifications } from "@/hooks/useUnreadNotifications";

export default function NotificationsBell() {
  const unread = useUnreadNotifications();
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    getNotifications(false, 10, 0).then((d) => setItems(d.items)).finally(() => setLoading(false));
  }, [open]);

  async function onClickItem(n: NotificationItem) {
    await markRead(n.id);
    const href =
      n.target_type === "post" ? `/posts/${n.target_id}` :
      n.target_type === "comment" ? `/posts/${n.target_id}` :
      "/notifications";
    window.location.href = href;
  }

  return (
    <div className="relative">
      <button onClick={() => setOpen((s) => !s)} className="relative rounded p-2 hover:bg-gray-100">
        🔔
        {unread > 0 && (
          <span className="absolute -top-1 -right-1 rounded-full bg-red-500 text-white text-xs px-1">{unread}</span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-80 rounded border bg-white shadow">
          <div className="flex items-center justify-between p-2 border-b">
            <div className="font-medium">Notifications</div>
            <button className="text-xs underline" onClick={async () => { await markAllRead(); setItems([]); }}>
              Mark all read
            </button>
          </div>
          {loading ? (
            <div className="p-3 text-sm text-gray-500">Loading…</div>
          ) : items.length === 0 ? (
            <div className="p-3 text-sm text-gray-500">You’re all caught up.</div>
          ) : (
            <ul className="max-h-96 overflow-y-auto">
              {items.map((n) => (
                <li key={n.id} className="p-3 border-b hover:bg-gray-50 cursor-pointer" onClick={() => onClickItem(n)}>
                  <div className="text-sm">
                    <span className={!n.is_read ? "font-semibold" : ""}>{n.action.replaceAll("_", " ")}</span>
                  </div>
                  <div className="text-xs text-gray-500">{new Date(n.created_at).toLocaleString()}</div>
                </li>
              ))}
            </ul>
          )}
          <div className="p-2 text-right">
            <Link href="/notifications" className="text-xs underline">View all</Link>
          </div>
        </div>
      )}
    </div>
  );
}
