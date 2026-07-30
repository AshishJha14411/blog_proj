"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import DOMPurify from "isomorphic-dompurify";
import { getPostById, updatePost, Post } from "@/services/postService";
import { sendFeedback } from "@/services/storyService";
import { getErrorMessage } from "@/lib/errors";

type LengthLabel = "flash" | "short" | "medium" | "long" | "";

export default function EditAIStoryPage() {
  const router = useRouter();
  const { postId } = useParams() as { postId: string };

  const [post, setPost] = useState<Post | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  // form fields
  const [title, setTitle] = useState("");
  const [summary, setSummary] = useState("");
  const [genre, setGenre] = useState("");
  const [tone, setTone] = useState("");
  const [lengthLabel, setLengthLabel] = useState<LengthLabel>("");
  const [feedback, setFeedback] = useState("");

  // generation/preview
  const [regenBusy, setRegenBusy] = useState(false);
  const [previewHTML, setPreviewHTML] = useState<string>("");

  useEffect(() => {
    // `router` is deliberately excluded from deps — Next's useRouter returns
    // a new reference each render, which would re-fire this effect every
    // parent re-render and re-fetch the post for nothing.
    let cancelled = false;
    (async () => {
      try {
        const p = await getPostById(postId);
        if (cancelled) return;
        if (p.source !== "ai") {
          // The /posts route was renamed to /userStory (W2 fix).
          router.replace(`/userStory/${postId}/edit`);
          return;
        }
        setPost(p);
        setTitle(p.title || "");
        setSummary(p.summary || p.header || "");
        setGenre(p.genre || "");
        setTone(p.tone || "");
        setLengthLabel((p.length_label as LengthLabel) || "");
        setPreviewHTML(p.content || "");
      } catch (e) {
        if (!cancelled) setErr(getErrorMessage(e, "Failed to load story."));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [postId]);

  const sanitizedPreview = useMemo(
    () => DOMPurify.sanitize(previewHTML || ""),
    [previewHTML]
  );

  async function onRegenerate() {
    if (!feedback.trim()) {
      setErr("Please add feedback for regeneration.");
      return;
    }
    setErr(null);
    setRegenBusy(true);
    try {
      // F8: sendFeedback expects a UUID *string* — Number() would produce NaN.
      const updated = await sendFeedback(postId, feedback);
      setPreviewHTML(updated.content || "");
      // Regenerate only ever runs on an already-loaded post, so `old` is
      // non-null here — just bump the version off the fresh response.
      setPost((old) => (old ? { ...old, version: updated.version ?? old.version } : old));
      setFeedback("");
    } catch (e) {
      setErr(getErrorMessage(e, "Regeneration failed."));
    } finally {
      setRegenBusy(false);
    }
  }

  async function onSave() {
    if (!title.trim()) {
      setErr("Title is required.");
      return;
    }
    setErr(null);
    try {
      await updatePost(postId, {
        title,
        content: previewHTML,
      });
      router.push(`/stories/${postId}`);
    } catch (e) {
      setErr(getErrorMessage(e, "Failed to save."));
    }
  }

  if (loading) return <div className="p-6 text-center">Loading…</div>;
  if (err) return <div className="p-6 text-center text-red-600">{err}</div>;
  if (!post) return <div className="p-6 text-center">Not found.</div>;

  return (
    <div className="max-w-5xl mx-auto p-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="space-y-4">
        <h1 className="text-xl font-semibold">Edit AI Story</h1>

        <label className="block text-sm">Title</label>
        <input className="w-full border rounded p-2" value={title} onChange={e=>setTitle(e.target.value)} />

        <label className="block text-sm">Short summary (blurb)</label>
        <textarea className="w-full border rounded p-2" rows={2} value={summary} onChange={e=>setSummary(e.target.value)} />

        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="block text-sm">Genre</label>
            <input className="w-full border rounded p-2" value={genre} onChange={e=>setGenre(e.target.value)} />
          </div>
          <div>
            <label className="block text-sm">Tone</label>
            <input className="w-full border rounded p-2" value={tone} onChange={e=>setTone(e.target.value)} />
          </div>
          <div>
            <label className="block text-sm">Length</label>
            <select className="w-full border rounded p-2" value={lengthLabel} onChange={e=>setLengthLabel(e.target.value as LengthLabel)}>
              <option value="">—</option>
              <option value="flash">flash</option>
              <option value="short">short</option>
              <option value="medium">medium</option>
              <option value="long">long</option>
            </select>
          </div>
        </div>

        <label className="block text-sm">Feedback to AI (what to change)</label>
        <textarea className="w-full border rounded p-2" rows={4} value={feedback} onChange={e=>setFeedback(e.target.value)} placeholder="Tighten pacing, add clearer dialogue beats, add SFX cues…"/>

        <div className="flex gap-3">
          <button onClick={onRegenerate} disabled={regenBusy || !feedback.trim()} className="px-4 py-2 rounded bg-black text-white disabled:opacity-60">
            {regenBusy ? "Regenerating…" : "Regenerate Preview"}
          </button>
          <button onClick={onSave} className="px-4 py-2 rounded border">Save to Post</button>
        </div>
      </div>

      <div>
        <div className="mb-2 text-sm text-gray-600">Preview (HTML)</div>
        <div className="prose max-w-none border rounded p-4"
             dangerouslySetInnerHTML={{ __html: sanitizedPreview }} />
      </div>
    </div>
  );
}
