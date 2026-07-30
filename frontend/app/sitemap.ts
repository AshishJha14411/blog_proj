/**
 * Dynamic sitemap — lists every published story so search engines can
 * discover and index them. A content site without this is largely invisible
 * to Google. Regenerated on request (server-side); Next serves it at
 * /sitemap.xml.
 */
import type { MetadataRoute } from "next";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface StoryRow {
  id: string;
  updated_at?: string | null;
  created_at?: string | null;
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const staticRoutes: MetadataRoute.Sitemap = [
    { url: `${SITE_URL}/`, changeFrequency: "daily", priority: 1 },
    { url: `${SITE_URL}/userStory`, changeFrequency: "daily", priority: 0.9 },
    { url: `${SITE_URL}/tags`, changeFrequency: "weekly", priority: 0.5 },
  ];

  let stories: StoryRow[] = [];
  try {
    // Published-only list (anonymous request); cap to a reasonable page.
    const res = await fetch(`${API_URL}/api/v1/stories/?limit=100`, {
      next: { revalidate: 3600 }, // cache the fetch for an hour
    });
    if (res.ok) {
      const data = await res.json();
      stories = Array.isArray(data?.items) ? data.items : [];
    }
  } catch {
    // A sitemap that's missing story URLs is better than a 500; degrade.
  }

  const storyRoutes: MetadataRoute.Sitemap = stories.map((s) => ({
    // Public read view lives at /userStory/{id} (where PostCard links).
    url: `${SITE_URL}/userStory/${s.id}`,
    lastModified: s.updated_at || s.created_at || undefined,
    changeFrequency: "weekly",
    priority: 0.7,
  }));

  return [...staticRoutes, ...storyRoutes];
}
