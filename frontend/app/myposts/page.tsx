
'use client';

import React, { useState, useEffect } from 'react';
import { getMyPost } from '@/services/postService';
import { Post } from '@/services/postService';
import PostCard from '@/components/common/PostCard'; // We are reusing the smart PostCard
import { useHydratedAuth } from '@/hooks/useHydratedAuth';
import { useRouter } from 'next/navigation';

export default function MyPostsPage() {
  const [posts, setPosts] = useState<Post[]>([]);
  const [loading, setLoading] = useState(true);
  const { isAuthenticated, isHydrated } = useHydratedAuth();
  const router = useRouter();

  useEffect(() => {
    if (isHydrated && !isAuthenticated) {
      router.push('/login');
      return;
    }

    if (isAuthenticated) {
      const fetchPosts = async () => {
        try {
          const response = await getMyPost();
          setPosts(response.items);
        } catch (err) {
          console.error('Failed to fetch posts');
        } finally {
          setLoading(false);
        }
      };
      fetchPosts();
    }
  }, [isAuthenticated, isHydrated, router]);

  if (!isHydrated || loading) {
    return <p className="p-8 text-center">Loading your posts...</p>;
  }

  return (
    <main className="mx-auto max-w-5xl p-8 font-sans">
      <h1 className="mb-8 text-3xl font-bold text-text">My Posts</h1>
      <div className="grid grid-cols-1 gap-8 md:grid-cols-2 lg:grid-cols-3">
        {posts.length > 0 ? (
          posts.map((post) => <PostCard key={post.id} post={post} />)
        ) : (
          <p className="col-span-full text-center text-text-light">
            You haven't created any posts yet.
          </p>
        )}
      </div>
    </main>
  );
}

