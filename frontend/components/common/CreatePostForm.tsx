'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { createPost } from '@/services/postService';
import Input from '@/components/ui/Input';
import Textarea from '@/components/ui/Textarea';
import Button from '@/components/ui/Button';
import FormLabel from '@/components/ui/FormLabel';
import TagInput from './TagInput';

export default function CreatePostForm() {
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [error, setError] = useState('');
  const router = useRouter();
  const [tag_names, setTag_names] = useState<string[]>([]);
  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError('');
    try {
      const newPost = await createPost({ title, content,tag_names });
      // Redirect to the new post's page after creation
      router.push(`/userStory/${newPost.id}`);
    } catch (err) {
      setError('Failed to create post. Please try again.');
      console.error(err);
    }
  };

  const words = content.trim() ? content.trim().split(/\s+/).length : 0;

  return (
    <div className="mx-auto max-w-3xl rounded-2xl border border-border-soft bg-surface p-8 shadow-soft sm:p-10">
      <span className="mb-3 inline-flex items-center gap-2 rounded-full border border-border-soft bg-surface-muted px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-text-subtle">
        <span className="h-1 w-1 rounded-full bg-primary" />
        Draft
      </span>
      <h1 className="mb-2 font-display text-3xl font-bold text-text">Write a New Story</h1>
      <p className="mb-8 text-sm text-text-light">
        Give it a title, tell the story, and tag it so readers can find it.
      </p>

      <form className="space-y-6" onSubmit={handleSubmit}>
        <div>
          <FormLabel htmlFor="title">Title</FormLabel>
          <Input
            id="title"
            type="text"
            required
            placeholder="A title worth clicking"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="!text-lg"
          />
        </div>
        <div>
          <div className="flex items-baseline justify-between">
            <FormLabel htmlFor="content">Content</FormLabel>
            {/* Live count: the only feedback a long-form editor really owes you. */}
            <span className="text-xs text-text-subtle">
              {words} {words === 1 ? 'word' : 'words'}
            </span>
          </div>
          <Textarea
            id="content"
            required
            rows={10}
            placeholder="Once upon a time…"
            value={content}
            onChange={(e) => setContent(e.target.value)}
          />
        </div>
        <div>
          <FormLabel htmlFor="tags">Tags</FormLabel>
          <TagInput tags={tag_names} setTags={setTag_names} />
        </div>
        {error && (
          <p className="rounded-xl border border-red-500/25 bg-red-500/10 px-4 py-3 text-sm text-red-600 dark:text-red-300">
            {error}
          </p>
        )}
        <div className="flex items-center gap-3 border-t border-border-soft pt-6">
          <Button type="submit">Publish Story</Button>
          <span className="text-xs text-text-subtle">
            Published stories are screened before they reach the feed.
          </span>
        </div>
      </form>
    </div>
  );
}
