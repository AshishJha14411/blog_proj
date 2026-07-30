/**
 * TanStack Query hooks — the app's server-state layer.
 *
 * Each hook wraps an existing service call in `useQuery`, so pages stop
 * hand-rolling useEffect + loading/error/cancelled flags (the race and
 * "setState after unmount" bugs from the audit). Query keys are centralized
 * so mutations can invalidate precisely.
 */
import { useQuery } from "@tanstack/react-query";

import { getMyBookmarks } from "@/services/userService";
import { getNotifications } from "@/services/notificationService";
import { getAllPosts, getMyPost } from "@/services/postService";

export const queryKeys = {
  bookmarks: ["bookmarks"] as const,
  notifications: (unreadOnly: boolean, offset: number) =>
    ["notifications", { unreadOnly, offset }] as const,
  stories: (limit: number, offset: number, tag?: string | null) =>
    ["stories", { limit, offset, tag }] as const,
  myStories: (limit: number, offset: number) =>
    ["my-stories", { limit, offset }] as const,
};

export function useBookmarks(enabled = true) {
  return useQuery({
    queryKey: queryKeys.bookmarks,
    queryFn: async () => (await getMyBookmarks()).items,
    enabled,
  });
}

export function useNotifications(unreadOnly = false, limit = 10, offset = 0, enabled = true) {
  return useQuery({
    queryKey: queryKeys.notifications(unreadOnly, offset),
    queryFn: async () => getNotifications(unreadOnly, limit, offset),
    enabled,
  });
}

export function useStories(limit = 10, offset = 0, tag: string | null = null) {
  return useQuery({
    queryKey: queryKeys.stories(limit, offset, tag),
    queryFn: async () => getAllPosts(limit, offset, tag),
  });
}

export function useMyStories(limit = 10, offset = 0, enabled = true) {
  return useQuery({
    queryKey: queryKeys.myStories(limit, offset),
    queryFn: async () => (await getMyPost(limit, offset)).items,
    enabled,
  });
}
