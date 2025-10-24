"use client";

import { useState } from "react";
import { publishStory, unpublishStory } from "@/services/storyService";

export default function PublishControls({
  postId,
  isPublished,
}: {
  postId: string;
  isPublished: boolean;
}) {
  const [loading, setLoading] = useState(false);
  const [state, setState] = useState(isPublished);
  const [err, setErr] = useState<string | null>(null);

  async function toggle() {
    setLoading(true);
    setErr(null);
    try {
      if (state) {
        await unpublishStory(postId);
        setState(false);
      } else {
        await publishStory(postId);
        setState(true);
      }
    } catch (e: any) {
      setErr(e?.response?.data?.detail || e.message || "Action failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex items-center gap-3">
      <button
        className="rounded-md border px-3 py-2 disabled:opacity-60"
        onClick={toggle}
        disabled={loading}
      >
        {state ? "Unpublish" : "Publish"}
      </button>
      {err && <span className="text-sm text-red-700">{err}</span>}
    </div>
  );
}
