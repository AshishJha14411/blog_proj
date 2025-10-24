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
      console.log(title,content,tag_names)
      // Redirect to the new post's page after creation
      router.push(`/userStory/${newPost.id}`);
    } catch (err) {
      setError('Failed to create post. Please try again.');
      console.error(err);
    }
  };

  return (
    <div className="mx-auto max-w-2xl rounded-lg bg-background-alt p-8 shadow-md">
      <h1 className="mb-6 text-3xl font-bold text-text">Create a New Post</h1>
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
        <div>
          <FormLabel htmlFor="tags">Tags</FormLabel>
          <TagInput tags={tag_names} setTags={setTag_names} />
        </div>
        {error && <p className="text-sm text-red-500">{error}</p>}
        <div>
          <Button type="submit">Publish Post</Button>
        </div>
      </form>
    </div>
  );
}
