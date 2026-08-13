"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import Button from "@/components/ui/Button";
import FormLabel from "@/components/ui/FormLabel";
import Input from "@/components/ui/Input";
import Select from "@/components/ui/Select";
import Textarea from "@/components/ui/Textarea";
import { generateStoryStream, StoryGenerateIn } from "@/services/storyService";

export default function GenerateStoryPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [streamText, setStreamText] = useState("");

  const [form, setForm] = useState<StoryGenerateIn>({
    title: "",
    summary: "",
    prompt: "",
    genre: "",
    tone: "",
    length_label: "short",
    cover_image_url: "",
    publish_now: false,
    temperature: 0.8,
    // No hardcoded model here — let the backend's LLM_MODEL setting decide
    // (app/llm/adapter.py falls back to it when model is unset). Two
    // independently-hardcoded model names — one here, one in .env — is
    // exactly how this broke: neither matched, and only this one was ever
    // actually used, silently masking the other.
  });

  const onChange = <K extends keyof StoryGenerateIn>(k: K, v: StoryGenerateIn[K]) =>
    setForm((s) => ({ ...s, [k]: v }));

async function onSubmit(e: React.FormEvent) {
  e.preventDefault();

  if (!form.prompt?.trim()) {
    setErr("Prompt is required");
    return;
  }

  setLoading(true);
  setErr(null);
  setStreamText("");

  const payload: StoryGenerateIn = {
    ...form,
    cover_image_url: form.cover_image_url?.trim() ? form.cover_image_url : null,
    length_label: form.length_label || "short",
    title: form.title?.trim() || null,
    summary: form.summary?.trim() || null,
    genre: form.genre?.trim() || null,
    tone: form.tone?.trim() || null
  };

  await generateStoryStream(payload, {
    onDelta: (text) => setStreamText((prev) => prev + text),
    onDone: ({ story_id }) => {
      // The story is saved. Navigate to it (it may be `pending` moderation
      // briefly if publish_now was set — the author can view their own).
      router.push(`/stories/${story_id}`);
    },
    onError: (message) => {
      setErr(message);
      setLoading(false);
    },
  });
}

  return (
    <main className="relative overflow-hidden font-sans">
      <div aria-hidden="true" className="aurora opacity-70" />
      <div
        aria-hidden="true"
        className="bg-dots mask-radial pointer-events-none absolute inset-0 opacity-60"
      />

      <div className="relative mx-auto max-w-6xl px-6 py-14">
        <div className="mb-10 max-w-2xl">
          <span className="inline-flex items-center gap-2 rounded-full border border-border-soft bg-surface/70 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-text-subtle backdrop-blur-sm">
            <span className="h-1 w-1 rounded-full bg-primary" />
            AI studio
          </span>
          <h1 className="mt-4 font-display text-4xl font-bold tracking-tight text-text">
            Generate a Story
          </h1>
          <p className="mt-3 text-text-light">
            Describe what you want and watch the draft arrive line by line. You can rewrite it
            with feedback before anyone else sees it.
          </p>
        </div>

        {err && (
          <div className="mb-6 rounded-2xl border border-red-500/25 bg-red-500/10 p-4 text-sm text-red-600 dark:text-red-300">
            {err}
          </div>
        )}

        <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          {/* ------------------------------------------------------- the brief */}
          <form
            onSubmit={onSubmit}
            className="space-y-5 rounded-2xl border border-border-soft bg-surface p-6 shadow-soft sm:p-8"
          >
            <div>
              <FormLabel htmlFor="gen-title">Title (optional)</FormLabel>
              <Input
                id="gen-title"
                value={form.title ?? ""}
                onChange={(e) => onChange("title", e.target.value)}
                placeholder="Untitled Story"
              />
            </div>

            <div>
              <FormLabel htmlFor="gen-summary">Short description / summary</FormLabel>
              <Textarea
                id="gen-summary"
                rows={2}
                value={form.summary ?? ""}
                onChange={(e) => onChange("summary", e.target.value)}
                placeholder="A quick blurb readers see first"
              />
            </div>

            <div>
              <FormLabel htmlFor="gen-prompt">Theme / instructions (prompt)</FormLabel>
              <Textarea
                id="gen-prompt"
                rows={6}
                required
                value={form.prompt}
                onChange={(e) => onChange("prompt", e.target.value)}
                placeholder="e.g., A sci-fi story about a courier who delivers memories across planets..."
              />
            </div>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              <div>
                <FormLabel htmlFor="gen-genre">Genre</FormLabel>
                <Input
                  id="gen-genre"
                  value={form.genre ?? ""}
                  onChange={(e) => onChange("genre", e.target.value)}
                  placeholder="sci-fi, fantasy…"
                />
              </div>
              <div>
                <FormLabel htmlFor="gen-tone">Tone</FormLabel>
                <Input
                  id="gen-tone"
                  value={form.tone ?? ""}
                  onChange={(e) => onChange("tone", e.target.value)}
                  placeholder="dark, hopeful…"
                />
              </div>
              <div>
                <FormLabel htmlFor="gen-length">Length</FormLabel>
                <Select
                  id="gen-length"
                  value={form.length_label ?? "short"}
                  onChange={(e) => onChange("length_label", e.target.value as StoryGenerateIn['length_label'])}
                >
                  <option value="flash">flash</option>
                  <option value="short">short</option>
                  <option value="medium">medium</option>
                  <option value="long">long</option>
                </Select>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div>
                <FormLabel htmlFor="gen-cover">Cover image URL (optional)</FormLabel>
                <Input
                  id="gen-cover"
                  value={form.cover_image_url ?? ""}
                  onChange={(e) => onChange("cover_image_url", e.target.value)}
                  placeholder="https://…"
                />
              </div>
              <div>
                <FormLabel htmlFor="gen-temp">Temperature</FormLabel>
                <Input
                  id="gen-temp"
                  type="number"
                  step="0.1"
                  min={0}
                  max={2}
                  value={form.temperature ?? 0.8}
                  onChange={(e) => onChange("temperature", Number(e.target.value))}
                />
                <p className="mt-1.5 text-xs text-text-subtle">
                  Lower is steadier, higher is stranger.
                </p>
              </div>
            </div>

            <label className="flex cursor-pointer items-center gap-3 rounded-xl border border-border-soft bg-surface-muted/60 px-4 py-3">
              <input
                type="checkbox"
                checked={form.publish_now ?? false}
                onChange={(e) => onChange("publish_now", e.target.checked)}
                className="h-4 w-4 accent-[var(--accent-primary)]"
              />
              <span className="text-sm text-text-light">Publish immediately (if not flagged)</span>
            </label>

            <div className="flex flex-wrap gap-3 border-t border-border-soft pt-5">
              <Button type="submit" disabled={loading}>
                {loading ? "Generating..." : "Generate Story"}
              </Button>
              <Button variant="secondary" type="button" onClick={() => router.push("/myposts")}>
                Cancel
              </Button>
            </div>
          </form>

          {/* ------------------------------------------------------ the output */}
          <div className="lg:sticky lg:top-24 lg:self-start">
            <div className="rounded-2xl border border-border-soft bg-surface p-6 shadow-soft sm:p-8">
              <div className="mb-4 flex items-center gap-2 border-b border-border-soft pb-4">
                <span
                  aria-hidden="true"
                  className={`h-2 w-2 rounded-full ${
                    loading ? 'animate-pulse-soft bg-emerald-500' : 'bg-border-strong'
                  }`}
                />
                <span className="text-sm font-medium text-text">
                  {loading ? (streamText ? 'Writing your story…' : 'Warming up…') : 'Preview'}
                </span>
              </div>

              {loading || streamText ? (
                <div
                  className="prose-story prose-story--compact max-h-[60vh] overflow-y-auto"
                  // Live preview of the author's own generation; the final story
                  // page sanitizes with DOMPurify before public display.
                  dangerouslySetInnerHTML={{
                    __html: streamText || "<p class='shimmer-text'>Thinking…</p>",
                  }}
                />
              ) : (
                <p className="py-10 text-center text-sm text-text-subtle">
                  Your draft will appear here as it&apos;s written.
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
