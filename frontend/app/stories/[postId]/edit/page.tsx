"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import DOMPurify from "isomorphic-dompurify";
import { getPostById, updatePost, Post } from "@/services/postService";
import { sendFeedback } from "@/services/storyService";

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
  const [lengthLabel, setLengthLabel] = useState<"flash"|"short"|"medium"|"long"|"">("");
  const [feedback, setFeedback] = useState("");

  // generation/preview
  const [regenBusy, setRegenBusy] = useState(false);
  const [previewHTML, setPreviewHTML] = useState<string>("");

  useEffect(() => {
    (async () => {
      try {
        const p = await getPostById(postId);
        if (p.source !== "ai") {
          router.replace(`/posts/${postId}/edit`); 
          return;
        }
        setPost(p);
        setTitle(p.title || "");
        setSummary(p.summary || p.header || "");
        setGenre(p.genre || "");
        setTone(p.tone || "");
        setLengthLabel((p.length_label as any) || "");
        setPreviewHTML(p.content || "");
      } catch (e: any) {
        setErr(e?.response?.data?.detail || "Failed to load story.");
      } finally {
        setLoading(false);
      }
    })();
  }, [postId, router]);

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
      const updated = await sendFeedback(Number(postId), feedback);
      setPreviewHTML(updated.content || "");
      setPost((old) => (old ? { ...old, version: updated.version } : updated as any));
      setFeedback("");
    } catch (e: any) {
      setErr(e?.response?.data?.detail || e.message || "Regeneration failed.");
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
      } as any);
      router.push(`/stories/${postId}`);
    } catch (e: any) {
      setErr(e?.response?.data?.detail || "Failed to save.");
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
            <select className="w-full border rounded p-2" value={lengthLabel} onChange={e=>setLengthLabel(e.target.value as any)}>
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
