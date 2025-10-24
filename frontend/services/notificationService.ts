import api from "@/lib/axios";

export interface NotificationItem {
  id: string;
  action: string;
  target_type?: string | null;
  target_id?: string | null;
  is_read: boolean;
  created_at: string;
  actor?: { id: string; username: string } | null;
}

export interface NotificationList {
  total: number;
  // backend also returns limit/offset, extra fields are fine
  items: NotificationItem[];
}

export async function getNotifications(unreadOnly = false, limit = 10, offset = 0) {
  const { data } = await api.get<NotificationList>("/me/notifications", {
    params: { unread_only: unreadOnly, limit, offset }, // <-- param name
  });
  return data;
}

export async function markRead(id: string) {
  await api.post(`/me/notifications/${id}/read`, {}); // <-- ensure leading slash + correct prefix
}

export async function markAllRead() {
  await api.post(`/me/notifications/read_all`, {});
}

export async function getUnreadCount() {
  const { data } = await api.get<{ count: number }>(`/me/notifications/unread_count`);
  return data.count;
}
