"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { generateStory, StoryGenerateIn } from "@/services/storyService";

export default function GenerateStoryPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

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
    model_name: "gemini-2.5-pro",
  });

  const onChange = (k: keyof StoryGenerateIn, v: any) =>
    setForm((s) => ({ ...s, [k]: v }));

async function onSubmit(e: React.FormEvent) {
  e.preventDefault();
  setLoading(true);
  setErr(null);

  if (!form.prompt?.trim()) {
    setErr("Prompt is required");
    setLoading(false);
    return;
  }

  const payload: StoryGenerateIn = {
    ...form,
    cover_image_url: form.cover_image_url?.trim() ? form.cover_image_url : null,
    length_label: form.length_label || "short",
    title: form.title?.trim() || null,
    summary: form.summary?.trim() || null,
    genre: form.genre?.trim() || null,
    tone: form.tone?.trim() || null
  };

  try {
    const created = await generateStory(payload);
    router.push(`/stories/${created.id}`);
  } catch (e: any) {
    if (Array.isArray(e?.response?.data?.detail)) {
      setErr(e.response.data.detail.map((d: any) => d.msg).join(", "));
    } else {
      setErr(e?.message || "Failed to generate");
    }
  } finally {
    setLoading(false);
  }
}



  return (
    <div className="max-w-2xl mx-auto p-6 space-y-6">
      <h1 className="text-2xl font-semibold">Generate a Story</h1>

      {err && (
        <div className="rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-700">
          {err}
        </div>
      )}

      <form onSubmit={onSubmit} className="space-y-4">
        <div>
          <label className="block text-sm mb-1">Title (optional)</label>
          <input
            className="w-full rounded-md border p-2"
            value={form.title ?? ""}
            onChange={(e) => onChange("title", e.target.value)}
            placeholder="Untitled Story"
          />
        </div>

        <div>
          <label className="block text-sm mb-1">Short Description / Summary</label>
          <textarea
            className="w-full rounded-md border p-2"
            rows={2}
            value={form.summary ?? ""}
            onChange={(e) => onChange("summary", e.target.value)}
            placeholder="A quick blurb readers see first"
          />
        </div>

        <div>
          <label className="block text-sm mb-1">Theme / Instructions (Prompt)</label>
          <textarea
            className="w-full rounded-md border p-2"
            rows={6}
            required
            value={form.prompt}
            onChange={(e) => onChange("prompt", e.target.value)}
            placeholder="e.g., A sci-fi story about a courier who delivers memories across planets..."
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm mb-1">Genre</label>
            <input
              className="w-full rounded-md border p-2"
              value={form.genre ?? ""}
              onChange={(e) => onChange("genre", e.target.value)}
              placeholder="sci-fi, fantasy, romance…"
            />
          </div>
          <div>
            <label className="block text-sm mb-1">Tone</label>
            <input
              className="w-full rounded-md border p-2"
              value={form.tone ?? ""}
              onChange={(e) => onChange("tone", e.target.value)}
              placeholder="dark, hopeful, humorous…"
            />
          </div>
          <div>
            <label className="block text-sm mb-1">Length</label>
            <select
              className="w-full rounded-md border p-2"
              value={form.length_label ?? "short"}
              onChange={(e) => onChange("length_label", e.target.value as any)}
            >
              <option value="flash">flash</option>
              <option value="short">short</option>
              <option value="medium">medium</option>
              <option value="long">long</option>
            </select>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm mb-1">Cover Image URL (optional)</label>
            <input
              className="w-full rounded-md border p-2"
              value={form.cover_image_url ?? ""}
              onChange={(e) => onChange("cover_image_url", e.target.value)}
              placeholder="https://…"
            />
          </div>
          <div>
            <label className="block text-sm mb-1">Temperature</label>
            <input
              type="number"
              step="0.1"
              min={0}
              max={2}
              className="w-full rounded-md border p-2"
              value={form.temperature ?? 0.8}
              onChange={(e) => onChange("temperature", Number(e.target.value))}
            />
          </div>
        </div>

        <div className="flex items-center gap-3">
          <label className="inline-flex items-center gap-2">
            <input
              type="checkbox"
              checked={form.publish_now ?? false}
              onChange={(e) => onChange("publish_now", e.target.checked)}
            />
            <span>Publish immediately (if not flagged)</span>
          </label>
        </div>

        <div className="flex gap-3">
          <button
            type="submit"
            disabled={loading}
            className="rounded-md bg-black text-white px-4 py-2 disabled:opacity-60"
          >
            {loading ? "Generating..." : "Generate Story"}
          </button>
          <button
            type="button"
            onClick={() => router.push("/posts")}
            className="rounded-md border px-4 py-2"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
