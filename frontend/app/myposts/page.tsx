'use client';

import React, { useEffect } from 'react';
import PostCard from '@/components/common/PostCard'; // We are reusing the smart PostCard
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

  if (!isHydrated || (isAuthenticated && isLoading)) {
    return <p className="p-8 text-center">Loading your stories...</p>;
  }

  return (
    <main className="mx-auto max-w-5xl p-8 font-sans">
      <h1 className="mb-8 text-3xl font-bold text-text">My Stories</h1>
      <div className="grid grid-cols-1 gap-8 md:grid-cols-2 lg:grid-cols-3">
        {posts.length > 0 ? (
          posts.map((post) => <PostCard key={post.id} post={post} />)
        ) : (
          <p className="col-span-full text-center text-text-light">
            You haven&apos;t created any posts yet.
          </p>
        )}
      </div>
    </main>
  );
}
