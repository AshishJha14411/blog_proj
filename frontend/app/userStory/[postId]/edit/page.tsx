'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter,useParams } from 'next/navigation';
import { getPostById, updatePost } from '@/services/postService';
import Input from '@/components/ui/Input';
import Textarea from '@/components/ui/Textarea';
import Button from '@/components/ui/Button';
import FormLabel from '@/components/ui/FormLabel';

export default function EditPostPage() {
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const router = useRouter();
  const params = useParams()
  const postId = params.postId as string

  // Fetch the existing post data when the component loads
  useEffect(() => {
    const fetchPost = async () => {
      try {
        const post = await getPostById(postId);
        setTitle(post.title);
        setContent(post.content);
      } catch {
        setError('Failed to load post data.');
      } finally {
        setLoading(false);
      }
    };
    fetchPost();
  }, [params.postId]);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError('');
    try {
      await updatePost(postId, { title, content });
      router.push(`/userStory/${postId}`); // Redirect back to the post
    } catch {
      setError('Failed to update post.');
    }
  };

  if (loading) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-14">
        <div className="skeleton h-8 w-48" />
        <div className="skeleton mt-8 h-10 w-full" />
        <div className="skeleton mt-6 h-56 w-full" />
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-14">
      <div className="rounded-2xl border border-border-soft bg-surface p-8 shadow-soft sm:p-10">
        <div className="mb-8 flex items-center justify-between gap-4">
          <div>
            <h1 className="font-display text-3xl font-bold text-text">Edit Story</h1>
            <p className="mt-1 text-sm text-text-light">Changes go live as soon as you save.</p>
          </div>
          <Link
            href={`/userStory/${postId}`}
            className="text-sm text-text-subtle transition-colors hover:text-primary-strong"
          >
            Cancel
          </Link>
        </div>

        <form className="space-y-6" onSubmit={handleSubmit}>
          <div>
            <FormLabel htmlFor="title">Title</FormLabel>
            <Input
              id="title"
              type="text"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="!text-lg"
            />
          </div>
          <div>
            <FormLabel htmlFor="content">Content</FormLabel>
            <Textarea
              id="content"
              required
              rows={14}
              value={content}
              onChange={(e) => setContent(e.target.value)}
            />
          </div>
          {error && (
            <p className="rounded-xl border border-red-500/25 bg-red-500/10 px-4 py-3 text-sm text-red-600 dark:text-red-300">
              {error}
            </p>
          )}
          <div className="border-t border-border-soft pt-6">
            <Button type="submit">Save Changes</Button>
          </div>
        </form>
      </div>
    </main>
  );
}
