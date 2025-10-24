"use client";

import { useState } from "react";
import { sendFeedback } from "@/services/storyService";

export default function RegenerateWithFeedback({ postId }: { postId: string }) {
  const [feedback, setFeedback] = useState("");
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  async function onRegenerate() {
    if (!feedback.trim()) return;
    setLoading(true);
    setMsg(null);
    setErr(null);
    try {
      const updated = await sendFeedback(postId, feedback);
      setMsg(`Regenerated (version ${updated.version ?? "?"}). Refresh to see changes if not auto-rendered.`);
      setFeedback("");
      // If your post page fetches on client, you could also trigger a re-fetch here.
    } catch (e: any) {
      setErr(e?.response?.data?.detail || e.message || "Failed to regenerate");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-2">
      <label className="block text-sm">Feedback for rewrite</label>
      <textarea
        className="w-full rounded-md border p-2"
        rows={3}
        value={feedback}
        onChange={(e) => setFeedback(e.target.value)}
        placeholder="Tell the AI what to fix (pacing, tone, ending, characters...)"
      />
      <div className="flex gap-3">
        <button
          className="rounded-md bg-black text-white px-3 py-2 disabled:opacity-60"
          onClick={onRegenerate}
          disabled={loading || !feedback.trim()}
        >
          {loading ? "Regenerating..." : "Apply Feedback & Regenerate"}
        </button>
      </div>
      {msg && <div className="text-sm text-green-700">{msg}</div>}
      {err && <div className="text-sm text-red-700">{err}</div>}
    </div>
  );
}
