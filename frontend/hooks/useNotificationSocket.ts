"use client";
/**
 * WHY: the notifications bell used to poll `/notifications/unread-count`
 * every 5 minutes — cheap per client, but N users × 12 pings/hour scales.
 * Phase 3 replaces that with a push channel over WebSocket.
 *
 * WHAT: `useNotificationSocket(onMessage)` opens a ticket-authenticated
 * WS, calls `onMessage(payload)` for each server frame, and manages the
 * lifecycle (reconnect with backoff, tab-visibility, graceful downgrade
 * back to polling after too many failed reconnects).
 *
 * WHY-THIS-WAY:
 *   - Ticket-flow instead of token-in-URL: matches backend `ws/tickets.py`.
 *   - Exponential backoff with jitter: standard curve for reconnection
 *     without thundering-herd against the server.
 *   - Give up after N failures and return `downgraded=true` so the caller
 *     falls back to the existing polling hook (see useUnreadNotifications).
 */
import { useEffect, useRef, useState } from "react";

import { API_URL } from "@/lib/axios";
import axiosInstance from "@/lib/axios";
import { useAuthStore } from "@/stores/authStore";

// recommended by claude opus 4.7: values below are the ones the backend was
// designed for. Change these only if you also tune the corresponding
// server-side ping cadence (25s) and ticket TTL (30s).
const MAX_ATTEMPTS = 6;
const BACKOFF_BASE_MS = 1_000;
const BACKOFF_MAX_MS = 30_000;

export type NotificationMessage = {
  type: string;
  id?: string;
  action?: string;
  actor_id?: string | null;
  target_type?: string | null;
  target_id?: string | null;
  created_at?: string | null;
};

export type SocketState = {
  connected: boolean;
  downgraded: boolean;
};

/**
 * WHAT: convert `http(s)://…` to `ws(s)://…` so we can reuse API_URL.
 */
function toWsUrl(httpUrl: string): string {
  return httpUrl.replace(/^http/, "ws");
}

/**
 * WHY: jitter breaks thundering-herd. Every client that lost connection at
 * the same second must not reconnect at the same second.
 */
function backoffFor(attempt: number): number {
  const base = Math.min(BACKOFF_BASE_MS * 2 ** attempt, BACKOFF_MAX_MS);
  return base * (0.75 + Math.random() * 0.5); // ±25%
}

export function useNotificationSocket(
  onMessage: (msg: NotificationMessage) => void,
): SocketState {
  const [state, setState] = useState<SocketState>({
    connected: false,
    downgraded: false,
  });
  const attemptsRef = useRef(0);
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const cancelled = useRef(false);

  useEffect(() => {
    cancelled.current = false;
    const { isAuthenticated } = useAuthStore.getState();
    if (!isAuthenticated) return;

    const connect = async () => {
      if (cancelled.current) return;
      try {
        // WHAT: mint a fresh 30s ticket on every (re)connect. Absolute URL on
        // purpose: /ws/ticket is top-level, NOT under the axios /api/v1 base.
        const { data } = await axiosInstance.post<{ ticket: string }>(
          `${API_URL}/ws/ticket`,
        );
        if (cancelled.current) return;

        const url = `${toWsUrl(API_URL)}/ws/notifications?ticket=${encodeURIComponent(
          data.ticket,
        )}`;
        const ws = new WebSocket(url);
        socketRef.current = ws;

        ws.onopen = () => {
          attemptsRef.current = 0;
          setState({ connected: true, downgraded: false });
        };

        ws.onmessage = (event) => {
          try {
            const payload = JSON.parse(event.data) as NotificationMessage;
            // WHY: server sends {type:"ping"} every 25s as a keepalive.
            // Clients ignore pings — they exist only to keep proxies happy.
            if (payload.type === "ping") return;
            onMessage(payload);
          } catch {
            // Malformed frame — ignore rather than dropping the socket.
          }
        };

        ws.onclose = () => {
          setState((s) => ({ ...s, connected: false }));
          scheduleReconnect();
        };

        ws.onerror = () => {
          // onerror fires just before onclose — let onclose do the work.
        };
      } catch {
        scheduleReconnect();
      }
    };

    const scheduleReconnect = () => {
      if (cancelled.current) return;
      attemptsRef.current += 1;
      if (attemptsRef.current > MAX_ATTEMPTS) {
        // WHY: after enough failures, stop trying — caller falls back to
        // polling. Never make real-time the ONLY path.
        setState({ connected: false, downgraded: true });
        return;
      }
      const delay = backoffFor(attemptsRef.current - 1);
      reconnectTimer.current = setTimeout(connect, delay);
    };

    // WHY: throttle reconnect attempts when the tab is hidden — background
    // tabs don't need real-time and hammering during throttled JS wastes
    // battery. When the tab comes back, force a fresh attempt.
    const onVisibilityChange = () => {
      if (document.visibilityState === "visible" && !socketRef.current) {
        attemptsRef.current = 0;
        connect();
      }
    };
    document.addEventListener("visibilitychange", onVisibilityChange);

    connect();

    return () => {
      cancelled.current = true;
      document.removeEventListener("visibilitychange", onVisibilityChange);
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      if (socketRef.current) {
        try {
          socketRef.current.close();
        } catch {
          // ignore
        }
      }
      socketRef.current = null;
    };
    // WHY: onMessage is intentionally not in deps — the caller passes a
    // fresh reference every render. Wrap in useRef there if you need
    // per-render state; otherwise this hook stays stable.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return state;
}
