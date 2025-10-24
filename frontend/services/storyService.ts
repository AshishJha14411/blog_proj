import api from "@/lib/axios";

export type LengthLabel = "flash" | "short" | "medium" | "long";

export interface StoryGenerateIn {
  title?: string | null;
  summary?: string | null;
  prompt: string;
  genre?: string | null;
  tone?: string | null;
  length_label?: LengthLabel | null;
  cover_image_url?: string | null;
  publish_now?: boolean;
  temperature?: number;
  model_name?: string;
}

export interface PostOut {
  id: string;
  title: string;
  header?: string | null;
  content: string;
  cover_image_url?: string | null;
  user_id: string;
  is_published: boolean;
  created_at: string;
  updated_at: string;

  // new fields the API returns (make them optional to avoid breakage)
  source?: "ai" | "user";
  genre?: string | null;
  tone?: string | null;
  length_label?: LengthLabel | null;
  summary?: string | null;
  status?: "draft" | "generated" | "published" | "rejected";
  version?: number;
  words_count?: number;
  last_feedback?: string | null;

  // existing extras from your PostOut
  is_liked_by_user?: boolean;
  is_bookmarked_by_user?: boolean;
}

export async function generateStory(payload: StoryGenerateIn): Promise<PostOut> {
  const { data } = await api.post<PostOut>("/stories/generate", payload);
  return data;
}

export async function sendFeedback(postId: string, feedback: string): Promise<PostOut> {
  const { data } = await api.post<PostOut>(`/stories/${postId}/feedback`, { feedback });
  return data;
}

export async function publishStory(postId: string): Promise<PostOut> {
  const { data } = await api.post<PostOut>(`/stories/${postId}/publish`, {});
  return data;
}

export async function unpublishStory(postId: string): Promise<PostOut> {
  const { data } = await api.post<PostOut>(`/stories/${postId}/unpublish`, {});
  return data;
}
