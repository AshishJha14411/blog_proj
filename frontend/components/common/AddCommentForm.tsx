'use client';

import React, { useState } from 'react';
import Textarea from '@/components/ui/Textarea';
import Button from '@/components/ui/Button';

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
      console.log("On Adding comment check:", newComments)
      onCommentAdded(newComments); 
      setContent(''); 
    } catch (err) {
      setError('Failed to post comment. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="mt-8">
      <h3 className="text-xl font-bold text-text mb-4">Add a Comment</h3>
      <Textarea
        value={content}
        onChange={(e) => setContent(e.target.value)}
        placeholder="Share your thoughts..."
        rows={4}
        required
        disabled={loading}
      />
      {error && <p className="text-sm text-red-500 mt-2">{error}</p>}
      <div className="mt-4">
        <Button type="submit" disabled={loading}>
          {loading ? 'Posting...' : 'Post Comment'}
        </Button>
      </div>
    </form>
  );
}
