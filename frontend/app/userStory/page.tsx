import { getAllPosts } from '@/services/postService';
import PostCard from '@/components/common/PostCard';
import EmptyState from '@/components/ui/EmptyState';
import PageHeader from '@/components/ui/PageHeader';
import Link from 'next/link';
import nextDynamic from 'next/dynamic';
import React from 'react';
export const dynamic = 'force-dynamic';
// Client-only AdSlot inside a Server Component
const AdSlot = nextDynamic(() => import('@/components/ads/AdSlot'), { ssr: true });

export default async function AllPostsPage({ searchParams }: { searchParams?: Promise<Record<string, string | string[] | undefined>> }) {
  const limit = 10;
  const resolvedSearchParams = await searchParams;
  const page = Number(resolvedSearchParams?.page) || 1;
  const offset = (page - 1) * limit;

  const { total, items: posts } = await getAllPosts(limit, offset);
  const totalPages = Math.ceil(total / limit);

  const pagerLink =
    'inline-flex items-center gap-2 rounded-full border border-border-soft bg-surface px-5 py-2.5 text-sm font-medium text-text transition-all hover:-translate-y-0.5 hover:border-primary/50 hover:text-primary-strong';

  return (
    <main className="mx-auto max-w-6xl px-6 py-14 font-sans">
      <PageHeader
        eyebrow="The feed"
        title="Stories"
        description="Everything published on Quill & Code, newest first."
        actions={
          <Link
            href="/userStory/create"
            className="rounded-full bg-primary px-5 py-2.5 text-sm font-semibold text-on-primary transition-all hover:-translate-y-0.5 hover:bg-primary-light"
          >
            Write a story
          </Link>
        }
      />

      {/* Banner ad above grid */}
      <div className="mb-8">
        <AdSlot />
      </div>

      {posts.length > 0 ? (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          {posts.map((post, idx) => (
            <React.Fragment key={post.id}>
              <PostCard post={post} />
              {/* Insert an ad every 6 cards */}
              {((idx + 1) % 6 === 0) && (
                <div className="md:col-span-2 lg:col-span-3">
                  <AdSlot />
                </div>
              )}
            </React.Fragment>
          ))}
        </div>
      ) : (
        <EmptyState
          title="No stories yet"
          description="Nothing has been published on this page. Try the first page, or write something."
        />
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="mt-14 flex items-center justify-center gap-4">
          {page > 1 ? (
            <Link href={`/userStory?page=${page - 1}`} className={pagerLink}>
              ← Previous
            </Link>
          ) : (
            <span className="w-28" />
          )}
          <span className="text-sm text-text-subtle">
            Page {page} of {totalPages}
          </span>
          {page < totalPages ? (
            <Link href={`/userStory?page=${page + 1}`} className={pagerLink}>
              Next →
            </Link>
          ) : (
            <span className="w-28" />
          )}
        </div>
      )}

      {/* Footer banner */}
      <div className="mt-12">
        <AdSlot />
      </div>
    </main>
  );
}
