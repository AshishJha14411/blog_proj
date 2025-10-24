"use client";
import { useEffect, useState } from "react";
import { getUnreadCount } from "@/services/notificationService";

export function useUnreadNotifications(pollMs = 300000) {
  const [count, setCount] = useState(0);

  async function load() {
    try { setCount(await getUnreadCount()); } catch {}
  }

  useEffect(() => {
    load();
    const id = setInterval(load, pollMs);
    return () => clearInterval(id);
  }, []);

  return count;
}
