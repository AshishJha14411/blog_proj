"use client";

import { useEffect, useState } from "react";
import { approvePost, fetchModPost, rejectPost } from "@/services/moderationService";
import { useParams, useRouter } from "next/navigation";
import { useModGuard } from "@/hooks/useModGuard";
import DOMPurify from "isomorphic-dompurify";

export default function ModItemPage() {
  const { ready, isMod } = useModGuard();
  const params = useParams();
  const router = useRouter();
  const id = Number(params.id);
  const [post, setPost] = useState<any>(null);
  const [note, setNote] = useState("");

  useEffect(() => {
    if (!ready || !isMod || !id) return;
    fetchModPost(id).then(setPost);
  }, [ready, isMod, id]);

  if (!isMod) return null;
  if (!post) return <div className="p-6">Loading…</div>;

  return (
    <main className="mx-auto max-w-4xl p-6">
      <h1 className="text-xl font-semibold mb-2">{post.title}</h1>
      <div className="text-sm text-gray-600 mb-4">
        by {post.user?.username} · {new Date(post.created_at).toLocaleString()}
      </div>
      <div className="prose"
        dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(post.content || "") }} />

      {/* Flags (if your API returns them, otherwise hide) */}
      {Array.isArray(post.flags) && post.flags.length > 0 && (
        <div className="mt-6 border-t pt-4">
          <h2 className="font-medium mb-2">Flags</h2>
          <ul className="text-sm list-disc pl-5">
            {post.flags.map((f: any) => (
              <li key={f.id}>{f.reason} — {new Date(f.created_at).toLocaleString()}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="mt-6 flex gap-2">
        <input
          className="border rounded p-2 flex-1"
          placeholder="Optional moderator note / rejection reason"
          value={note}
          onChange={(e) => setNote(e.target.value)}
        />
        <button
          className="rounded bg-green-600 text-white px-4 py-2"
          onClick={async () => { await approvePost(id, note); router.push("/admin/mod/queue"); }}
        >
          Approve
        </button>
        <button
          className="rounded bg-red-600 text-white px-4 py-2"
          onClick={async () => { await rejectPost(id, note || "rejected"); router.push("/admin/mod/queue"); }}
        >
          Reject
        </button>
      </div>
    </main>
  );
}
