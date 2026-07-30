/**
 * robots.txt — allow crawling of public content, point crawlers at the
 * sitemap, and keep them out of authenticated/admin areas.
 */
import type { MetadataRoute } from "next";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/admin/", "/profile", "/bookmarks", "/notifications", "/myposts"],
    },
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
