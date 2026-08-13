"use client";

import { useParams } from "next/navigation";

import AIStoryEditor from "@/components/story/AIStoryEditor";

export default function EditAIStoryPage() {
  const { postId } = useParams() as { postId: string };
  // The /posts route was renamed to /userStory (W2 fix).
  return <AIStoryEditor postId={postId} nonAiRedirect={`/userStory/${postId}/edit`} />;
}
