import api from "@/lib/axios";

export interface NotificationItem {
  id: number;
  action: string;
  target_type?: string | null;
  target_id?: number | null;
  is_read: boolean;
  created_at: string;
  actor?: { id: number; username: string } | null;
}

export interface NotificationList {
  total: number;
  items: NotificationItem[];
}

export async function getNotifications(only_unread = false, limit = 10, offset = 0) {
  const { data } = await api.get<NotificationList>("/notifications", {
    params: { only_unread, limit, offset },
  });
  return data;
}

export async function markRead(id: number) {
  await api.post(`/notifications/${id}/read`, {});
}

export async function markAllRead() {
  await api.post(`/notifications/read_all`, {});
}

export async function getUnreadCount() {
  const { data } = await api.get<{ count: number }>("/notifications/unread_count");
  return data.count;
}
