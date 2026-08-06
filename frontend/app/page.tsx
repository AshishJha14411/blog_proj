import Link from 'next/link';
import React from 'react';

import PostCard from '@/components/common/PostCard';
import { getAllPosts, getPopularPosts, type Post } from '@/services/postService';

export const dynamic = 'force-dynamic';

/**
 * Home.
 *
 * WHY THIS EXISTS: `/` was a placeholder ("Welcome to the Blog") while the only
 * real feed lived at `/userStory`, so the Home link in the navbar led nowhere
 * useful. It now leads with the stories readers actually engaged with, because
 * a strictly reverse-chronological feed buries good writing the moment anything
 * newer is published.
 *
 * A Server Component: both lists are public, so they render on the server with
 * no auth token and no client-side loading flash.
 */
export default async function Home() {
  // Fetched in parallel — these are independent endpoints and awaiting them in
  // sequence would add a full round trip to the page's time-to-first-byte.
  // `catch` per request so one failing section degrades instead of 500-ing the
  // whole page (the backend scales to zero, so a cold start can time out).
  const [popular, latest] = await Promise.all([
    getPopularPosts(6).catch(() => [] as Post[]),
    getAllPosts(6, 0).then((r) => r.items).catch(() => [] as Post[]),
  ]);

  // Don't repeat a story in "Latest" if it's already shown above.
  const popularIds = new Set(popular.map((p) => p.id));
  const latestFiltered = latest.filter((p) => !popularIds.has(p.id)).slice(0, 3);

  return (
    <main className="mx-auto max-w-6xl px-6 py-12 font-sans">
      <section className="mb-14 text-center">
        <h1 className="text-4xl font-bold text-text sm:text-5xl">Quill &amp; Code</h1>
        <p className="mx-auto mt-4 max-w-2xl text-lg text-text-light">
          Write your own stories, or bring an idea and let AI draft it with you —
          then publish it to readers.
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <Link
            href="/stories/generate"
            className="rounded-md bg-primary px-5 py-2.5 font-medium text-white transition hover:opacity-90"
          >
            Write with AI
          </Link>
          <Link
            href="/userStory"
            className="rounded-md border border-primary px-5 py-2.5 font-medium text-primary transition hover:bg-primary/5"
          >
            Browse stories
          </Link>
        </div>
      </section>

      {popular.length > 0 && (
        <section className="mb-14">
          <div className="mb-6 flex items-baseline justify-between">
            <h2 className="text-2xl font-bold text-text">Most loved stories</h2>
            <Link href="/userStory" className="text-sm text-primary hover:underline">
              View all
            </Link>
          </div>
          <div className="grid grid-cols-1 gap-8 md:grid-cols-2 lg:grid-cols-3">
            {popular.map((post) => (
              <PostCard key={post.id} post={post} showEngagement />
            ))}
          </div>
        </section>
      )}

      {latestFiltered.length > 0 && (
        <section>
          <div className="mb-6 flex items-baseline justify-between">
            <h2 className="text-2xl font-bold text-text">Fresh off the press</h2>
            <Link href="/userStory" className="text-sm text-primary hover:underline">
              View all
            </Link>
          </div>
          <div className="grid grid-cols-1 gap-8 md:grid-cols-2 lg:grid-cols-3">
            {latestFiltered.map((post) => (
              <PostCard key={post.id} post={post} />
            ))}
          </div>
        </section>
      )}

      {popular.length === 0 && latestFiltered.length === 0 && (
        <p className="rounded-lg border border-dashed p-12 text-center text-text-light">
          No stories published yet — be the first.
        </p>
      )}
    </main>
  );
}
