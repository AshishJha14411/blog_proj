'use client';

import React, { useEffect } from 'react';
import Link from 'next/link';
import PostCard from '@/components/common/PostCard'; // We are reusing the smart PostCard
import EmptyState from '@/components/ui/EmptyState';
import PageHeader from '@/components/ui/PageHeader';
import { CardGridSkeleton } from '@/components/ui/Skeleton';
import { useHydratedAuth } from '@/hooks/useHydratedAuth';
import { useRouter } from 'next/navigation';
import { useMyStories } from '@/hooks/queries';

export default function MyPostsPage() {
  const { isAuthenticated, isHydrated } = useHydratedAuth();
  const router = useRouter();

  // TanStack owns the fetch + cache + loading/error state — the old
  // useEffect/useState/cancelled dance is gone. The query only runs once auth
  // has hydrated and the user is logged in (`enabled`).
  const { data: posts = [], isLoading } = useMyStories(10, 0, isHydrated && isAuthenticated);

  useEffect(() => {
    if (isHydrated && !isAuthenticated) router.push('/login');
  }, [isHydrated, isAuthenticated, router]);

  const published = posts.filter((p) => p.is_published).length;

  return (
    <main className="mx-auto max-w-6xl px-6 py-14 font-sans">
      <PageHeader
        eyebrow="Your work"
        title="My Stories"
        description={
          posts.length > 0
            ? `${posts.length} ${posts.length === 1 ? 'story' : 'stories'} · ${published} published`
            : 'Drafts and published stories, all in one place.'
        }
        actions={
          <Link
            href="/userStory/create"
            className="rounded-full bg-primary px-5 py-2.5 text-sm font-semibold text-on-primary transition-all hover:-translate-y-0.5 hover:bg-primary-light"
          >
            New story
          </Link>
        }
      />

      {!isHydrated || (isAuthenticated && isLoading) ? (
        <CardGridSkeleton count={3} />
      ) : posts.length > 0 ? (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          {posts.map((post) => (
            <PostCard key={post.id} post={post} />
          ))}
        </div>
      ) : (
        <EmptyState
          title="Nothing written yet"
          description="You haven't created any posts yet. Start from a blank page, or let AI draft the first version."
          action={
            <div className="flex flex-wrap justify-center gap-3">
              <Link
                href="/userStory/create"
                className="rounded-full bg-primary px-5 py-2.5 text-sm font-semibold text-on-primary transition-colors hover:bg-primary-light"
              >
                Write from scratch
              </Link>
              <Link
                href="/stories/generate"
                className="rounded-full border border-border-strong px-5 py-2.5 text-sm font-medium text-text transition-colors hover:border-primary/50 hover:text-primary-strong"
              >
                Write with AI
              </Link>
            </div>
          }
        />
      )}
    </main>
  );
}
