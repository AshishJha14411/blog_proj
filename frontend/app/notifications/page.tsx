"use client";

import { useEffect, useState } from "react";
import { getNotifications, markRead, NotificationItem } from "@/services/notificationService";

export default function NotificationsPage() {
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [total, setTotal] = useState(0);
  const [limit] = useState(20);
  const [offset, setOffset] = useState(0);

  async function load() {
    const res = await getNotifications(false, limit, offset);
    setItems(res.items);
    setTotal(res.total);
  }

  useEffect(() => { load(); }, [offset]);

  return (
    <main className="mx-auto max-w-3xl p-6">
      <h1 className="text-2xl font-semibold mb-4">Notifications</h1>
      {items.length === 0 ? (
        <div className="text-gray-500">No notifications.</div>
      ) : (
        <ul className="space-y-3">
          {items.map((n) => (
            <li key={n.id} className="border rounded p-3">
              <div className="flex justify-between">
                <div className={!n.is_read ? "font-medium" : ""}>{n.action.replaceAll("_"," ")}</div>
                {!n.is_read && (
                  <button className="text-xs underline" onClick={async () => { await markRead(n.id); load(); }}>
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
        <div>Showing {offset + 1}-{Math.min(offset + limit, total)} of {total}</div>
        <button className="rounded border px-3 py-1" disabled={offset + limit >= total} onClick={() => setOffset(offset + limit)}>Next</button>
      </div>
    </main>
  );
}
