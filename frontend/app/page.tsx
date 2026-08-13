import Link from 'next/link';
import React from 'react';

import PostCard from '@/components/common/PostCard';
import { SectionHeading } from '@/components/ui/PageHeader';
import EmptyState from '@/components/ui/EmptyState';
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
    <main className="font-sans">
      {/* ---------------------------------------------------------------- hero */}
      <section className="relative overflow-hidden px-6 pt-20 pb-24 sm:pt-28">
        <div aria-hidden="true" className="aurora" />
        <div
          aria-hidden="true"
          className="bg-dots mask-radial pointer-events-none absolute inset-0 opacity-70"
        />

        <div className="relative mx-auto max-w-3xl text-center">
          <span className="inline-flex items-center gap-2 rounded-full border border-border-soft bg-surface/70 px-3.5 py-1.5 text-xs font-medium text-text-light backdrop-blur-sm">
            <span className="relative flex h-1.5 w-1.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-70" />
              <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-primary" />
            </span>
            AI-assisted drafting, human-published
          </span>

          <h1 className="mt-7 font-display text-5xl leading-[1.05] font-bold tracking-tight sm:text-7xl">
            <span className="text-gradient">Quill &amp; Code</span>
          </h1>

          <p className="mx-auto mt-6 max-w-xl text-lg leading-relaxed text-text-light">
            Write your own stories, or bring an idea and let AI draft it with you — then publish
            it to readers.
          </p>

          <div className="mt-10 flex flex-wrap justify-center gap-3">
            {/* The one place the rotating conic border earns its keep: the
                primary action on the primary page. */}
            <Link
              href="/stories/generate"
              className="glow-border rounded-full bg-primary px-6 py-3 font-semibold text-on-primary transition-transform hover:-translate-y-0.5"
            >
              Write with AI
            </Link>
            <Link
              href="/userStory"
              className="rounded-full border border-border-strong bg-surface/70 px-6 py-3 font-medium text-text backdrop-blur-sm transition-all hover:-translate-y-0.5 hover:border-primary/50 hover:text-primary-strong"
            >
              Browse stories
            </Link>
          </div>
        </div>
      </section>

      <div className="mx-auto max-w-6xl px-6 pb-20">
        {/* ----------------------------------------------------------- popular */}
        {popular.length > 0 && (
          <section className="mb-20">
            <SectionHeading
              title="Most loved stories"
              hint="Ranked by what readers liked, saved and replied to."
              action={
                <Link
                  href="/userStory"
                  className="text-sm font-medium text-primary-strong transition-colors hover:underline"
                >
                  View all →
                </Link>
              }
            />
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
              {popular.map((post) => (
                <PostCard key={post.id} post={post} showEngagement />
              ))}
            </div>
          </section>
        )}

        {/* ------------------------------------------------------------ latest */}
        {latestFiltered.length > 0 && (
          <section className="mb-20">
            <SectionHeading
              title="Fresh off the press"
              hint="The newest writing on the platform."
              action={
                <Link
                  href="/userStory"
                  className="text-sm font-medium text-primary-strong transition-colors hover:underline"
                >
                  View all →
                </Link>
              }
            />
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
              {latestFiltered.map((post) => (
                <PostCard key={post.id} post={post} />
              ))}
            </div>
          </section>
        )}

        {popular.length === 0 && latestFiltered.length === 0 && (
          <EmptyState
            title="No stories published yet"
            description="The feed fills up as soon as the first story goes live. It could be yours."
            action={
              <Link
                href="/userStory/create"
                className="rounded-full bg-primary px-5 py-2.5 text-sm font-semibold text-on-primary transition-colors hover:bg-primary-light"
              >
                Write the first one
              </Link>
            }
          />
        )}

        {/* --------------------------------------------------------- how it works */}
        <section className="relative mt-4 overflow-hidden rounded-3xl border border-border-soft bg-surface-muted/50 px-6 py-14 sm:px-12">
          <div
            aria-hidden="true"
            className="bg-grid mask-radial pointer-events-none absolute inset-0"
          />
          <div className="relative">
            <h2 className="text-center font-display text-2xl font-bold text-text sm:text-3xl">
              Three steps from idea to reader
            </h2>
            <div className="mt-10 grid gap-8 sm:grid-cols-3">
              {[
                {
                  n: '01',
                  title: 'Start with a prompt',
                  body: 'Describe the story you want — genre, tone, length. Or skip it and write from scratch.',
                },
                {
                  n: '02',
                  title: 'Draft and refine',
                  body: 'Watch the draft stream in, then send feedback and regenerate until it reads right.',
                },
                {
                  n: '03',
                  title: 'Publish to readers',
                  body: 'Tag it, publish it, and it lands in the feed once it clears moderation.',
                },
              ].map((step) => (
                <div key={step.n} className="text-center sm:text-left">
                  <span className="font-display text-3xl font-bold text-primary/45">{step.n}</span>
                  <h3 className="mt-2 font-display text-lg font-bold text-text">{step.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-text-light">{step.body}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
