/**
 * Server component for a story page. Its ONLY job here is SEO: fetch the story
 * server-side and emit real <title>/<meta description>/OpenGraph tags so search
 * engines and social cards see the actual story, not an empty client shell.
 * The interactive body renders in StoryDetailClient.
 */
import type { Metadata } from "next";
import StoryDetailClient from "./StoryDetailClient";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";

async function fetchStory(postId: string) {
  try {
    const res = await fetch(`${API_URL}/api/v1/stories/${postId}`, { next: { revalidate: 300 } });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

function toDescription(html: string | undefined, fallback: string): string {
  if (!html) return fallback;
  const text = html.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
  return text.slice(0, 160) || fallback;
}

export async function generateMetadata(
  { params }: { params: Promise<{ postId: string }> },
): Promise<Metadata> {
  const { postId } = await params;
  const story = await fetchStory(postId);
  if (!story) {
    return { title: "Story not found — Quill & Code" };
  }
  const title = `${story.title} — Quill & Code`;
  const description = toDescription(story.content, story.header || story.summary || "A story on Quill & Code.");
  const url = `${SITE_URL}/userStory/${postId}`;
  return {
    title,
    description,
    alternates: { canonical: url },
    openGraph: {
      title,
      description,
      url,
      type: "article",
      images: story.cover_image_url ? [{ url: story.cover_image_url }] : undefined,
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
    },
  };
}

export default async function PostDetailPage(
  { params }: { params: Promise<{ postId: string }> },
) {
  const { postId } = await params;
  return <StoryDetailClient postId={postId} />;
}
