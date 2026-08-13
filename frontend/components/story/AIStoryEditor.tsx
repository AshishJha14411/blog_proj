"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import DOMPurify from "isomorphic-dompurify";

import Badge from "@/components/ui/Badge";
import Button from "@/components/ui/Button";
import FormLabel from "@/components/ui/FormLabel";
import Input from "@/components/ui/Input";
import Select from "@/components/ui/Select";
import Textarea from "@/components/ui/Textarea";
import { getErrorMessage } from "@/lib/errors";
import { getPostById, updatePost, Post } from "@/services/postService";
import { sendFeedback } from "@/services/storyService";

type LengthLabel = "flash" | "short" | "medium" | "long" | "";

/**
 * The AI story editor: brief on the left, live preview on the right.
 *
 * WHY A COMPONENT: /stories/[postId] and /stories/[postId]/edit were two
 * byte-for-byte copies of this screen that had already drifted (one had the
 * cancelled-fetch guard, the other didn't). They differ in exactly one thing —
 * where a *non*-AI post gets redirected — so that's the prop.
 */
export default function AIStoryEditor({
  postId,
  nonAiRedirect,
}: {
  postId: string;
  nonAiRedirect: string;
}) {
  const router = useRouter();

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
          router.replace(nonAiRedirect);
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
  }, [postId, nonAiRedirect]);

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

  if (loading) {
    return (
      <div className="mx-auto max-w-6xl px-6 py-14">
        <div className="skeleton h-8 w-56" />
        <div className="mt-8 grid gap-8 lg:grid-cols-2">
          <div className="skeleton h-96 rounded-2xl" />
          <div className="skeleton h-96 rounded-2xl" />
        </div>
      </div>
    );
  }

  if (err && !post) {
    return (
      <div className="mx-auto max-w-lg px-6 py-24 text-center">
        <p className="font-display text-2xl font-bold text-text">Couldn&apos;t open this story</p>
        <p className="mt-3 text-sm text-red-600 dark:text-red-300">{err}</p>
      </div>
    );
  }

  if (!post) return <div className="p-6 text-center text-text-light">Not found.</div>;

  return (
    <main className="mx-auto max-w-6xl px-6 py-14 font-sans">
      <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <Badge tone="rose">✦ AI-assisted</Badge>
          <h1 className="mt-3 font-display text-3xl font-bold text-text">Edit AI Story</h1>
          <p className="mt-1 text-sm text-text-light">
            Version {post.version ?? 1} · rewrite with feedback, then save to the post.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <Button variant="secondary" onClick={onSave}>Save to Post</Button>
        </div>
      </div>

      {err && (
        <div className="mb-6 rounded-2xl border border-red-500/25 bg-red-500/10 p-4 text-sm text-red-600 dark:text-red-300">
          {err}
        </div>
      )}

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
        <div className="space-y-5 rounded-2xl border border-border-soft bg-surface p-6 shadow-soft sm:p-8">
          <div>
            <FormLabel htmlFor="ai-title">Title</FormLabel>
            <Input id="ai-title" value={title} onChange={(e) => setTitle(e.target.value)} className="!text-lg" />
          </div>

          <div>
            <FormLabel htmlFor="ai-summary">Short summary (blurb)</FormLabel>
            <Textarea id="ai-summary" rows={2} value={summary} onChange={(e) => setSummary(e.target.value)} />
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div>
              <FormLabel htmlFor="ai-genre">Genre</FormLabel>
              <Input id="ai-genre" value={genre} onChange={(e) => setGenre(e.target.value)} />
            </div>
            <div>
              <FormLabel htmlFor="ai-tone">Tone</FormLabel>
              <Input id="ai-tone" value={tone} onChange={(e) => setTone(e.target.value)} />
            </div>
            <div>
              <FormLabel htmlFor="ai-length">Length</FormLabel>
              <Select
                id="ai-length"
                value={lengthLabel}
                onChange={(e) => setLengthLabel(e.target.value as LengthLabel)}
              >
                <option value="">—</option>
                <option value="flash">flash</option>
                <option value="short">short</option>
                <option value="medium">medium</option>
                <option value="long">long</option>
              </Select>
            </div>
          </div>

          <div className="border-t border-border-soft pt-5">
            <FormLabel htmlFor="ai-feedback">Feedback to AI (what to change)</FormLabel>
            <Textarea
              id="ai-feedback"
              rows={4}
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              placeholder="Tighten pacing, add clearer dialogue beats, add SFX cues…"
            />
            <div className="mt-4 flex flex-wrap gap-3">
              <Button onClick={onRegenerate} disabled={regenBusy || !feedback.trim()}>
                {regenBusy ? "Regenerating…" : "Regenerate Preview"}
              </Button>
            </div>
          </div>
        </div>

        <div className="lg:sticky lg:top-24 lg:self-start">
          <div className="rounded-2xl border border-border-soft bg-surface p-6 shadow-soft sm:p-8">
            <div className="mb-4 flex items-center justify-between border-b border-border-soft pb-4">
              <span className="text-sm font-medium text-text">Preview</span>
              {regenBusy && <span className="shimmer-text text-xs">Rewriting…</span>}
            </div>
            <div
              className="prose-story prose-story--compact max-h-[65vh] overflow-y-auto"
              dangerouslySetInnerHTML={{ __html: sanitizedPreview }}
            />
          </div>
        </div>
      </div>
    </main>
  );
}
