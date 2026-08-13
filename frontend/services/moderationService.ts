import api from "@/lib/axios";

export type StoryStatus = "draft" | "pending" | "generated" | "published" | "rejected";

export interface ModQueueParams {
  status?: StoryStatus | "flagged" | "";
  author_id?: string;
  tag?: string;
  q?: string;
  limit?: number;
  offset?: number;
}

export interface QueueItem {
  id: string;
  title: string;
  user: { id: string; username: string };
  status?: StoryStatus;
  is_flagged: boolean;
  created_at: string;
  updated_at: string;
  flag_count?: number;
}

export interface QueueResponse {
  total: number;
  items: QueueItem[];
}

export async function fetchModQueue(params: ModQueueParams): Promise<QueueResponse> {
  const { data } = await api.get<QueueResponse>("/moderation/queue", { params });
  return data;
}

export interface ModPostFlag {
  id: string;
  reason: string;
  created_at: string;
}

export interface ModPost {
  id: string;
  title: string;
  content: string;
  user?: { id: string; username: string };
  created_at: string;
  flags?: ModPostFlag[];
}

export async function fetchModPost(id: string): Promise<ModPost> {
  const { data } = await api.get<ModPost>(`/stories/${id}`);
  return data;
}

export async function approvePost(id: string, note?: string) {
  const { data } = await api.post(`/moderation/stories/${id}/approve`, { note });
  return data;
}

export async function rejectPost(id: string, reason?: string) {
  const { data } = await api.post(`/moderation/stories/${id}/reject`, { reason });
  return data;
}
