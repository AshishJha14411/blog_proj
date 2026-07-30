'use client';

import React, { useEffect } from 'react';
import PostCard from '@/components/common/PostCard';
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

  if (!isHydrated || isLoading) {
    return <p className="p-8 text-center">Loading your bookmarks...</p>;
  }
  if (isError) {
    return <p className="p-8 text-center text-red-500">Failed to fetch your bookmarks.</p>;
  }

  return (
    <main className="mx-auto max-w-5xl p-8 font-sans">
      <h1 className="mb-8 text-center text-4xl font-bold text-text">
        My Bookmarks
      </h1>

      {bookmarkedPosts.length > 0 ? (
        <div className="grid grid-cols-1 gap-8 md:grid-cols-2 lg:grid-cols-3">
          {bookmarkedPosts.map((post) => (
            <PostCard key={post.id} post={post} />
          ))}
        </div>
      ) : (
        <p className="text-center text-text-light">
          You haven&apos;t bookmarked any posts yet.
        </p>
      )}
    </main>
  );
}
