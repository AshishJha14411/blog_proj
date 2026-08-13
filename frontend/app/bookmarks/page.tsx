'use client';

import React, { useEffect } from 'react';
import Link from 'next/link';
import PostCard from '@/components/common/PostCard';
import EmptyState from '@/components/ui/EmptyState';
import PageHeader from '@/components/ui/PageHeader';
import { CardGridSkeleton } from '@/components/ui/Skeleton';
import { useHydratedAuth } from '@/hooks/useHydratedAuth';
import { useRouter } from 'next/navigation';
import { useBookmarks } from '@/hooks/queries';

export default function BookmarksPage() {
  const { isAuthenticated, isHydrated } = useHydratedAuth();
  const router = useRouter();

  // Redirect unauthenticated users once hydration settles.
  useEffect(() => {
    if (isHydrated && !isAuthenticated) router.push('/login');
  }, [isHydrated, isAuthenticated, router]);

  // TanStack Query handles loading/error/caching/cancellation — no manual
  // useEffect + `cancelled` flag. The query only runs once authenticated.
  const { data: bookmarkedPosts = [], isLoading, isError } = useBookmarks(
    isHydrated && isAuthenticated,
  );

  return (
    <main className="mx-auto max-w-6xl px-6 py-14 font-sans">
      <PageHeader
        eyebrow="Saved"
        title="My Bookmarks"
        description="Stories you kept for later."
      />

      {!isHydrated || isLoading ? (
        <CardGridSkeleton count={3} />
      ) : isError ? (
        <p className="rounded-2xl border border-red-500/25 bg-red-500/10 px-4 py-3 text-sm text-red-600 dark:text-red-300">
          Failed to fetch your bookmarks.
        </p>
      ) : bookmarkedPosts.length > 0 ? (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          {bookmarkedPosts.map((post) => (
            <PostCard key={post.id} post={post} />
          ))}
        </div>
      ) : (
        <EmptyState
          title="No bookmarks yet"
          description="Tap Save on any story and it lands here, waiting for you."
          action={
            <Link
              href="/userStory"
              className="rounded-full bg-primary px-5 py-2.5 text-sm font-semibold text-on-primary transition-colors hover:bg-primary-light"
            >
              Find something to read
            </Link>
          }
        />
      )}
    </main>
  );
}
