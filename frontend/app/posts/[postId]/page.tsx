
'use client';

import { getPostById } from '@/services/postService';
import React, { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import { Post } from '@/services/postService';
import PostActions from '@/components/common/PostActions';
import CommentList from '@/components/common/CommentList';
import InteractionButtons from '@/components/common/InteractionButtons';
export default function PostDetailPage() { 
  const [post, setPost] = useState<Post | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  const params = useParams();
  const postId = params.postId as string;

  useEffect(() => {
    if (!postId) return;

    const fetchPost = async () => {
      try {
        const postData = await getPostById(postId);
        setPost(postData);
      } catch (err) {
        setError('Post not found or you do not have permission to view it.');
      } finally {
        setLoading(false);
      }
    };

    fetchPost();
  }, [postId]);

  if (loading) {
    return <p className="p-8 text-center">Loading post...</p>;
  }

  if (error) {
    return <p className="p-8 text-center text-red-500">{error}</p>;
  }

  // This check prevents the "Cannot read properties of null" error
  if (!post) {
    return <p className="p-8 text-center">Post not found.</p>;
  }

  return (
    <main className="mx-auto max-w-3xl p-8 font-sans">
      <article>
        <h1 className="mb-4 text-4xl font-bold text-text">{post.title}</h1>
        <PostActions postAuthorId={post.user.id} postId={post.id} />
        <div className="mb-8 text-sm text-text-light">
          <span>By {post.user.username}</span>
          <span className="mx-2">•</span>
          <span>{new Date(post.created_at).toLocaleDateString()}</span>
        </div>
        <div className="prose lg:prose-xl text-text">
          <p>{post.content}</p>
        </div>
      </article>
      <div className="mt-8 border-t pt-4">
          <InteractionButtons
            postId={post.id}
            initialLiked={post.is_liked_by_user} // <-- Pass initial state
            initialBookmarked={post.is_bookmarked_by_user} // <-- Pass initial state
          />
          </div>
       <CommentList postId={postId} />
    </main>
  );
}
