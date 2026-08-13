'use client';

import React, { useState } from 'react';
import Textarea from '@/components/ui/Textarea';
import Button from '@/components/ui/Button';
import type { Comment } from '@/services/commentService';

interface AddCommentFormProps {
  postId: string;
  onCommentAdded: (newComment: Comment) => void; // Callback to update parent state
}

export default function AddCommentForm({ postId, onCommentAdded }: AddCommentFormProps) {
  const [content, setContent] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!content.trim()) return;
    
    setLoading(true);
    setError('');

    try {
      // We need to create this service function
      const { createComment } = await import('@/services/commentService');
      const newComments = await createComment(postId, content);
      onCommentAdded(newComments);
      setContent(''); 
    } catch {
      setError('Failed to post comment. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="mt-8 rounded-2xl border border-border-soft bg-surface p-5 shadow-soft"
    >
      <h3 className="mb-4 font-display text-lg font-bold text-text">Add a Comment</h3>
      <Textarea
        value={content}
        onChange={(e) => setContent(e.target.value)}
        placeholder="Share your thoughts..."
        rows={4}
        required
        disabled={loading}
        className="mt-0"
      />
      {error && (
        <p className="mt-3 rounded-xl border border-red-500/25 bg-red-500/10 px-3 py-2 text-sm text-red-600 dark:text-red-300">
          {error}
        </p>
      )}
      <div className="mt-4 flex items-center justify-between gap-3">
        <span className="text-xs text-text-subtle">Be kind. Be specific.</span>
        <Button type="submit" disabled={loading}>
          {loading ? 'Posting...' : 'Post Comment'}
        </Button>
      </div>
    </form>
  );
}
