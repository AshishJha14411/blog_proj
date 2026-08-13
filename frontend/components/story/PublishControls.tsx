"use client";

import { useState } from "react";
import { publishStory, unpublishStory } from "@/services/storyService";
import { getErrorMessage } from "@/lib/errors";

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
    } catch (e) {
      setErr(getErrorMessage(e, "Action failed"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mt-8 flex flex-wrap items-center gap-3 rounded-2xl border border-border-soft bg-surface-muted/60 p-4">
      <span
        className={`inline-flex items-center gap-1.5 text-sm font-medium ${
          state ? 'text-emerald-600 dark:text-emerald-400' : 'text-text-subtle'
        }`}
      >
        <span
          aria-hidden="true"
          className={`h-1.5 w-1.5 rounded-full ${state ? 'bg-emerald-500' : 'bg-text-subtle'}`}
        />
        {state ? 'Live' : 'Not published'}
      </span>
      <button
        className="ml-auto rounded-full border border-border-soft bg-surface px-4 py-2 text-sm font-medium text-text transition-colors hover:border-primary/40 hover:text-primary-strong disabled:opacity-60"
        onClick={toggle}
        disabled={loading}
      >
        {state ? "Unpublish" : "Publish"}
      </button>
      {err && <span className="text-sm text-red-600 dark:text-red-300">{err}</span>}
    </div>
  );
}
