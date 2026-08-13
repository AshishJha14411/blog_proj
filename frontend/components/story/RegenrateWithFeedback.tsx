"use client";

import { useState } from "react";
import Button from "@/components/ui/Button";
import Textarea from "@/components/ui/Textarea";
import { sendFeedback } from "@/services/storyService";
import { getErrorMessage } from "@/lib/errors";

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
    } catch (e) {
      setErr(getErrorMessage(e, "Failed to regenerate"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-2xl border border-border-soft bg-surface p-5 shadow-soft">
      <div className="mb-1 flex items-center gap-2">
        <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-primary/15 text-xs text-primary-strong">
          ✦
        </span>
        <h3 className="font-display text-lg font-bold text-text">Rewrite with feedback</h3>
      </div>
      <p className="mb-4 text-sm text-text-light">
        Say what should change and the model redrafts this story.
      </p>
      <Textarea
        rows={3}
        value={feedback}
        onChange={(e) => setFeedback(e.target.value)}
        placeholder="Tell the AI what to fix (pacing, tone, ending, characters...)"
        className="mt-0"
      />
      <div className="mt-4 flex gap-3">
        <Button onClick={onRegenerate} disabled={loading || !feedback.trim()}>
          {loading ? "Regenerating..." : "Apply Feedback & Regenerate"}
        </Button>
      </div>
      {msg && (
        <div className="mt-3 rounded-xl border border-emerald-500/25 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-700 dark:text-emerald-300">
          {msg}
        </div>
      )}
      {err && (
        <div className="mt-3 rounded-xl border border-red-500/25 bg-red-500/10 px-3 py-2 text-sm text-red-600 dark:text-red-300">
          {err}
        </div>
      )}
    </div>
  );
}
