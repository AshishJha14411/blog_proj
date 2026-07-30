"use client";
import { useEffect, useState } from "react";
import { getUnreadCount } from "@/services/notificationService";
import { useAuthStore } from "@/stores/authStore";

export function useUnreadNotifications(pollMs = 300_000) {
  const [count, setCount] = useState(0);
  // Subscribed (not getState()) so the effect re-runs the moment auth lands.
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const accessToken = useAuthStore((s) => s.accessToken);

  useEffect(() => {
    // WHY the gate: this hook used to fire on mount unconditionally, so an
    // anonymous visitor — and the brief window during login before the token is
    // stored — hit /me/notifications/unread_count without credentials and logged
    // a red 401 in the browser console. Nothing was broken (the catch below
    // swallowed it), but a live site should not surface errors for a case we
    // fully expect. Wait until we actually hold a token.
    if (!isAuthenticated || !accessToken) {
      setCount(0);
      return;
    }

    let cancelled = false;

    async function load() {
      try {
        const next = await getUnreadCount();
        if (!cancelled) setCount(next);
      } catch {
        // network hiccup — leave count as-is, the next tick will retry
      }
    }

    load();
    const id = setInterval(load, pollMs);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
    // pollMs in deps means changing the poll cadence tears down the old
    // interval instead of leaking one per change. The auth deps make the poll
    // start on login and stop on logout.
  }, [pollMs, isAuthenticated, accessToken]);

  return count;
}
