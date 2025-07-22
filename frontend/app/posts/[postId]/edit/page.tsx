'use client';

import React, { useState, useEffect } from 'react';
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
      } catch (err) {
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
      await updatePost(params.postId, { title, content });
      router.push(`/posts/${params.postId}`); // Redirect back to the post
    } catch (err) {
      setError('Failed to update post.');
    }
  };

  if (loading) return <p className="p-8 text-center">Loading...</p>;

  return (
    <main className="p-8">
      <div className="mx-auto max-w-2xl rounded-lg bg-background-alt p-8 shadow-md">
        <h1 className="mb-6 text-3xl font-bold text-text">Edit Post</h1>
        <form className="space-y-6" onSubmit={handleSubmit}>
          <div>
            <FormLabel htmlFor="title">Title</FormLabel>
            <Input
              id="title"
              type="text"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </div>
          <div>
            <FormLabel htmlFor="content">Content</FormLabel>
            <Textarea
              id="content"
              required
              rows={10}
              value={content}
              onChange={(e) => setContent(e.target.value)}
            />
          </div>
          {error && <p className="text-sm text-red-500">{error}</p>}
          <div>
            <Button type="submit">Save Changes</Button>
          </div>
        </form>
      </div>
    </main>
  );
}


