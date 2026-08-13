"use client";

import { useParams } from "next/navigation";

import AIStoryEditor from "@/components/story/AIStoryEditor";

/**
 * AI story workspace. Human-written posts don't belong here, so they bounce to
 * the plain editor (this route's own /edit child, which forwards them on to
 * /userStory/[postId]/edit).
 */
export default function AIStoryPage() {
  const { postId } = useParams() as { postId: string };
  return <AIStoryEditor postId={postId} nonAiRedirect={`/stories/${postId}/edit`} />;
}
