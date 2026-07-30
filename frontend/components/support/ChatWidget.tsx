"use client";
/**
 * WHY: floating support widget. Wires the backend /ws/support (Phase 4)
 * into a small chat UI with streaming render and an "escalate to human"
 * button.
 *
 * WHAT: state machine:
 *   idle → connecting → connected → streaming → done
 *   any of the above → disconnected → reconnect with backoff
 *
 * WHY-THIS-WAY:
 *   - Reuse the same ticket flow the notifications hook uses.
 *   - Deltas are appended to the current assistant message; done switches
 *     back to accepting user input.
 *   - Escalation is a single frame; server responds with `escalated`.
 */
import { useEffect, useMemo, useRef, useState } from "react";

import axiosInstance, { API_URL } from "@/lib/axios";
import { useAuthStore } from "@/stores/authStore";

type ChatRole = "user" | "assistant" | "system";
interface ChatMsg {
  role: ChatRole;
  content: string;
}

// recommended by claude opus 4.7: cap the visible history at 30 messages
// to match the server-side LTRIM cap. Same number in two places keeps the
// UI honest about what's actually persisted.
const MAX_MESSAGES = 30;

function toWsUrl(httpUrl: string): string {
  return httpUrl.replace(/^http/, "ws");
}

export default function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  // WHY: assistant streaming appends into the last message rather than
  // creating a new one per chunk. Ref avoids stale closures inside the
  // WebSocket event handlers.
  const streamingRef = useRef(false);

  useEffect(() => {
    if (!open || !isAuthenticated) return;
    let cancelled = false;

    const connect = async () => {
      try {
        // ABSOLUTE URL on purpose. The axios instance is based at
        // `${API_URL}/api/v1`, but the WebSocket routers are mounted TOP-LEVEL
        // on the backend (main.py keeps /ws outside the versioned prefix). A
        // relative "/ws/ticket" therefore resolved to /api/v1/ws/ticket, which
        // 404s — the ticket mint failed, so the socket never opened and the chat
        // silently did nothing. Confirmed in Cloud Run logs:
        //   POST /ws/ticket         -> 200
        //   POST /api/v1/ws/ticket  -> 404
        // Same reason useNotificationSocket builds this URL absolutely.
        const { data } = await axiosInstance.post<{ ticket: string }>(
          `${API_URL}/ws/ticket`,
        );
        if (cancelled) return;
        const ws = new WebSocket(
          `${toWsUrl(API_URL)}/ws/support?ticket=${encodeURIComponent(data.ticket)}`,
        );
        socketRef.current = ws;

        ws.onopen = () => setConnected(true);
        ws.onclose = () => setConnected(false);
        ws.onerror = () => setError("Connection lost. Retry in a moment.");

        ws.onmessage = (event) => {
          try {
            const frame = JSON.parse(event.data) as {
              type: string;
              text?: string;
              message?: string;
              ticket?: string;
            };
            if (frame.type === "ping") return;

            if (frame.type === "delta" && frame.text) {
              if (!streamingRef.current) {
                // Start a new assistant bubble to receive deltas.
                streamingRef.current = true;
                setMessages((prev) => [...prev, { role: "assistant", content: "" }]);
              }
              setMessages((prev) => {
                const next = [...prev];
                const last = next[next.length - 1];
                if (last && last.role === "assistant") {
                  next[next.length - 1] = { ...last, content: last.content + frame.text };
                }
                return next;
              });
              return;
            }

            if (frame.type === "done") {
              streamingRef.current = false;
              setBusy(false);
              return;
            }

            if (frame.type === "budget_exceeded") {
              streamingRef.current = false;
              setBusy(false);
              setError("Daily message limit reached. Come back tomorrow.");
              return;
            }

            if (frame.type === "escalated") {
              setMessages((prev) => [
                ...prev,
                {
                  role: "system",
                  content:
                    "A support agent has been notified. They'll follow up via email.",
                },
              ]);
              setBusy(false);
              return;
            }

            if (frame.type === "error" && frame.message) {
              streamingRef.current = false;
              setBusy(false);
              setError(frame.message);
              return;
            }
          } catch {
            // ignore malformed frames
          }
        };
      } catch {
        setError("Could not start chat. Please try again.");
      }
    };

    connect();
    return () => {
      cancelled = true;
      if (socketRef.current) {
        try {
          socketRef.current.close();
        } catch {
          // ignore
        }
      }
      socketRef.current = null;
      setConnected(false);
    };
  }, [open, isAuthenticated]);

  const send = () => {
    const text = input.trim();
    if (!text || busy || !socketRef.current || !connected) return;
    socketRef.current.send(JSON.stringify({ type: "user", content: text }));
    setMessages((prev) => [...prev, { role: "user" as const, content: text }].slice(-MAX_MESSAGES));
    setInput("");
    setBusy(true);
    setError(null);
  };

  const escalate = () => {
    if (!socketRef.current || !connected) return;
    socketRef.current.send(JSON.stringify({ type: "escalate", reason: "user_requested" }));
    setBusy(true);
  };

  const visibleMessages = useMemo(
    () => messages.slice(-MAX_MESSAGES),
    [messages],
  );

  if (!isAuthenticated) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50">
      {open ? (
        <div className="w-80 rounded-lg border bg-white shadow-lg flex flex-col max-h-[70vh]">
          <div className="flex items-center justify-between border-b p-2">
            <div className="font-medium">Support</div>
            <button
              className="text-sm text-gray-500 hover:text-black"
              onClick={() => setOpen(false)}
              aria-label="Close"
            >
              ✕
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-3 space-y-2 text-sm">
            {visibleMessages.length === 0 ? (
              <p className="text-gray-500">
                Hi! Ask about the platform, moderation, or your account.
              </p>
            ) : (
              visibleMessages.map((m, i) => (
                <div
                  key={i}
                  className={
                    m.role === "user"
                      ? "text-right"
                      : m.role === "system"
                        ? "text-center text-gray-500 text-xs italic"
                        : "text-left"
                  }
                >
                  <span
                    className={
                      m.role === "user"
                        ? "inline-block bg-blue-500 text-white rounded-lg px-2 py-1"
                        : m.role === "system"
                          ? ""
                          : "inline-block bg-gray-100 rounded-lg px-2 py-1"
                    }
                  >
                    {m.content || (busy && m.role === "assistant" ? "…" : "")}
                  </span>
                </div>
              ))
            )}
            {error && <p className="text-xs text-red-500 text-center">{error}</p>}
          </div>

          <div className="border-t p-2 space-y-2">
            <div className="flex gap-2">
              <input
                className="flex-1 rounded border p-1 text-sm"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    send();
                  }
                }}
                placeholder="Type a message…"
                disabled={busy || !connected}
              />
              <button
                className="rounded bg-black px-3 py-1 text-sm text-white disabled:opacity-50"
                onClick={send}
                disabled={busy || !connected || !input.trim()}
              >
                Send
              </button>
            </div>
            <button
              className="w-full text-xs text-gray-500 underline"
              onClick={escalate}
              disabled={busy || !connected}
            >
              Escalate to a human
            </button>
          </div>
        </div>
      ) : (
        <button
          onClick={() => setOpen(true)}
          className="rounded-full bg-black text-white shadow-lg h-12 w-12 flex items-center justify-center text-xl"
          aria-label="Open support chat"
        >
          💬
        </button>
      )}
    </div>
  );
}
