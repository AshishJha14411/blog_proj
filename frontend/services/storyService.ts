import api, { API_V1_URL } from "@/lib/axios";
import { useAuthStore } from "@/stores/authStore";

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
  status?: "draft" | "pending" | "generated" | "published" | "rejected";
  version?: number;
  words_count?: number;
  last_feedback?: string | null;

  // existing extras from your PostOut
  is_liked_by_user?: boolean;
  is_bookmarked_by_user?: boolean;
}

// Long-story generation can take up to ~2 minutes server-side, well past the
// axios default (30s). Override the timeout for these LLM calls specifically
// so the browser doesn't abort a request the backend is still working on.
const LLM_REQUEST_TIMEOUT_MS = 150_000;

export async function generateStory(payload: StoryGenerateIn): Promise<PostOut> {
  const { data } = await api.post<PostOut>("/stories/generate", payload, { timeout: LLM_REQUEST_TIMEOUT_MS });
  return data;
}

export interface StreamDone {
  story_id: string;
  status: string | null;
  title: string;
}

export interface StreamHandlers {
  onDelta: (text: string) => void;
  onDone: (info: StreamDone) => void;
  onError: (message: string) => void;
}

/**
 * Streams AI story generation over Server-Sent Events. Uses fetch + a
 * ReadableStream reader rather than the native EventSource, because
 * EventSource is GET-only and we need a POST body plus the Bearer token.
 * Each {type:"delta"} frame appends text; {type:"done"} carries the saved
 * story id to navigate to.
 */
export async function generateStoryStream(
  payload: StoryGenerateIn,
  handlers: StreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const token = useAuthStore.getState().accessToken;
  let res: Response;
  try {
    res = await fetch(`${API_V1_URL}/stories/generate/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      credentials: "include",
      body: JSON.stringify(payload),
      signal,
    });
  } catch {
    handlers.onError("Could not reach the server.");
    return;
  }

  if (!res.ok || !res.body) {
    handlers.onError(res.status === 429 ? "Rate limit reached. Try again shortly." : `Request failed (${res.status}).`);
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  // SSE frames are separated by a blank line ("\n\n"); each frame has a
  // "data:" line carrying our JSON payload.
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let sep: number;
    while ((sep = buffer.indexOf("\n\n")) !== -1) {
      const frame = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      const dataLine = frame.split("\n").find((l) => l.startsWith("data:"));
      if (!dataLine) continue;
      try {
        const evt = JSON.parse(dataLine.slice(5).trim());
        if (evt.type === "delta") handlers.onDelta(evt.text ?? "");
        else if (evt.type === "done") handlers.onDone(evt as StreamDone);
        else if (evt.type === "error") handlers.onError(evt.message ?? "Generation failed.");
      } catch {
        // ignore malformed frame
      }
    }
  }
}

export async function sendFeedback(
  postId: string,
  feedback: string,
  lengthLabel?: LengthLabel,
): Promise<PostOut> {
  // lengthLabel is optional and forwarded only when the caller supplies it —
  // omitting it keeps the story's existing length server-side. Without this the
  // length control on the preview page had no effect: every revision reused the
  // length the story was first generated at.
  const { data } = await api.post<PostOut>(
    `/stories/${postId}/feedback`,
    lengthLabel ? { feedback, length_label: lengthLabel } : { feedback },
    { timeout: LLM_REQUEST_TIMEOUT_MS },
  );
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
