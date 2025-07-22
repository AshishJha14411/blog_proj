
'use client';

import React, { useState, useEffect } from 'react';
import { getMyBookmarks } from '@/services/userService';
import { Post } from '@/services/postService';
import PostCard from '@/components/common/PostCard';
import { useHydratedAuth } from '@/hooks/useHydratedAuth';
import { useRouter } from 'next/navigation';

export default function BookmarksPage() {
  const [bookmarkedPosts, setBookmarkedPosts] = useState<Post[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const { isAuthenticated, isHydrated } = useHydratedAuth();
  const router = useRouter();

  useEffect(() => {
    // If the user is not authenticated after hydration, redirect to login
    if (isHydrated && !isAuthenticated) {
      router.push('/login');
      return;
    }

    // Only fetch if the user is authenticated
    if (isAuthenticated) {
      const fetchBookmarks = async () => {
        try {
          const response = await getMyBookmarks();
          setBookmarkedPosts(response.items);
        } catch (err) {
          setError('Failed to fetch your bookmarks.');
        } finally {
          setLoading(false);
        }
      };
      fetchBookmarks();
    }
  }, [isAuthenticated, isHydrated, router]);

  if (!isHydrated || loading) {
    return <p className="p-8 text-center">Loading your bookmarks...</p>;
  }
  
  if (error) {
    return <p className="p-8 text-center text-red-500">{error}</p>;
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
          You haven't bookmarked any posts yet.
        </p>
      )}
    </main>
  );
}
