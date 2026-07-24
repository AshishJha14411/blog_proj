"use client";
import { useEffect, useState } from "react";
import { getUnreadCount } from "@/services/notificationService";

export function useUnreadNotifications(pollMs = 300_000) {
  const [count, setCount] = useState(0);

  useEffect(() => {
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
    // interval instead of leaking one per change.
  }, [pollMs]);

  return count;
}
