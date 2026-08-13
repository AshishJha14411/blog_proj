"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { approvePost, fetchModPost, rejectPost, type ModPost } from "@/services/moderationService";
import { useParams, useRouter } from "next/navigation";
import Avatar from "@/components/ui/Avatar";
import Badge from "@/components/ui/Badge";
import Input from "@/components/ui/Input";
import { useModGuard } from "@/hooks/useModGuard";
import DOMPurify from "isomorphic-dompurify";

export default function ModItemPage() {
  const { ready, isMod } = useModGuard();
  const params = useParams();
  const router = useRouter();
  const id = params.id as string; // <-- keep as string (UUID)
  const [post, setPost] = useState<ModPost | null>(null);
  const [note, setNote] = useState("");

  useEffect(() => {
    if (!ready) return;
    if (!isMod) {
      router.replace("/"); // or /admin/mod/queue
      return;
    }
    if (!id) return;

    (async () => {
      try {
        const data = await fetchModPost(id);
        setPost(data);
      } catch {
        setPost(null);
      }
    })();
  }, [ready, isMod, id, router]);

  if (!isMod) return null;
  if (!ready || !post) {
    return (
      <main className="mx-auto max-w-4xl px-6 py-14">
        <div className="skeleton h-8 w-2/3" />
        <div className="skeleton mt-4 h-4 w-48" />
        <div className="skeleton mt-8 h-64 w-full rounded-2xl" />
      </main>
    );
  }

  const flags = Array.isArray(post.flags) ? post.flags : [];

  return (
    <main className="mx-auto max-w-4xl px-6 py-14">
      <Link
        href="/admin/mod/queue"
        className="inline-flex items-center gap-1.5 text-sm text-text-subtle transition-colors hover:text-primary-strong"
      >
        ← Back to queue
      </Link>

      <div className="mt-6 flex flex-wrap items-center gap-2">
        {flags.length > 0 && <Badge tone="warning" dot>{flags.length} flag{flags.length === 1 ? '' : 's'}</Badge>}
      </div>

      <h1 className="mt-3 font-display text-3xl font-bold text-text">{post.title}</h1>
      <div className="mt-4 flex items-center gap-2.5">
        <Avatar name={post.user?.username} size="sm" />
        <div className="text-sm text-text-light">
          {post.user?.username}
          <span className="mx-1.5 text-text-subtle">·</span>
          <span className="text-text-subtle">{new Date(post.created_at).toLocaleString()}</span>
        </div>
      </div>

      <div className="mt-8 rounded-2xl border border-border-soft bg-surface p-6 shadow-soft sm:p-8">
        <div
          className="prose-story"
          dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(post.content || "") }}
        />
      </div>

      {flags.length > 0 && (
        <div className="mt-8 rounded-2xl border border-amber-500/25 bg-amber-500/8 p-5">
          <h2 className="mb-3 font-semibold text-text">Why it was flagged</h2>
          <ul className="space-y-2 text-sm text-text-light">
            {flags.map((f) => (
              <li key={f.id} className="flex gap-2">
                <span aria-hidden="true" className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-amber-500" />
                <span>
                  {f.reason}
                  <span className="ml-2 text-xs text-text-subtle">
                    {new Date(f.created_at).toLocaleString()}
                  </span>
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Decision bar: the note applies to whichever action is taken, so it
          sits with the buttons rather than in a separate block. */}
      <div className="mt-8 flex flex-col gap-3 rounded-2xl border border-border-soft bg-surface-muted/60 p-4 sm:flex-row sm:items-center">
        <Input
          className="mt-0 flex-1"
          placeholder="Optional moderator note / rejection reason"
          value={note}
          onChange={(e) => setNote(e.target.value)}
        />
        <div className="flex gap-2">
          <button
            className="rounded-full border border-emerald-500/30 bg-emerald-500/12 px-5 py-2 text-sm font-semibold text-emerald-700 transition-colors hover:bg-emerald-500/20 dark:text-emerald-300"
            onClick={async () => {
              await approvePost(id, note);
              router.push("/admin/mod/queue");
            }}
          >
            Approve
          </button>
          <button
            className="rounded-full border border-red-500/30 bg-red-500/12 px-5 py-2 text-sm font-semibold text-red-600 transition-colors hover:bg-red-500/20 dark:text-red-300"
            onClick={async () => {
              await rejectPost(id, note || "rejected");
              router.push("/admin/mod/queue");
            }}
          >
            Reject
          </button>
        </div>
      </div>
    </main>
  );
}
