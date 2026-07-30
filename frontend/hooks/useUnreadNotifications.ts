"use client";
import { useQuery } from "@tanstack/react-query";

import { getUnreadCount } from "@/services/notificationService";
import { useAuthStore } from "@/stores/authStore";

/** Shared cache key — anything that changes read-state should invalidate this. */
export const unreadCountKey = ["notifications", "unread-count"] as const;

/**
 * Unread badge count.
 *
 * WHY TanStack rather than local state + setInterval: the count is server state
 * displayed in two places (this badge and the notifications page), and marking a
 * notification read has to update BOTH. With a local useState the badge kept a
 * private copy that only refreshed on its poll tick — and when the WebSocket is
 * healthy that tick is an hour — so "mark all read" visibly zeroed the list but
 * left a stale number on the bell. A shared query key makes invalidation the
 * mechanism instead of hoping the next poll arrives.
 *
 * WHY the auth gate: calling an authed endpoint while anonymous (or in the beat
 * between login and the token landing in the store) logged a red 401 in the
 * console on every page load.
 */
export function useUnreadNotifications(pollMs = 300_000) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const accessToken = useAuthStore((s) => s.accessToken);
  const enabled = Boolean(isAuthenticated && accessToken);

  const { data } = useQuery({
    queryKey: unreadCountKey,
    queryFn: getUnreadCount,
    enabled,
    refetchInterval: pollMs,
    // A failed count is cosmetic — don't retry-storm the API over a badge.
    retry: false,
    initialData: 0,
  });

  return enabled ? (data ?? 0) : 0;
}
