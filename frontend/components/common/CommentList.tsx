'use client';

import React, { useState, useEffect } from 'react';
import { getCommentsForPost, deleteComment, Comment } from '@/services/commentService';
import { useHydratedAuth } from '@/hooks/useHydratedAuth';
import Avatar from '@/components/ui/Avatar';
import AddCommentForm from './AddCommentForm';

interface CommentListProps {
  postId: string;
}

export default function CommentList({ postId }: CommentListProps) {
  const [comments, setComments] = useState<Comment[]>([]);
  const [loading, setLoading] = useState(true);
  const { user, isAuthenticated, isHydrated } = useHydratedAuth();
  
  // State to prevent hydration mismatch
  const [isClient, setIsClient] = useState(false);
  useEffect(() => {
    setIsClient(true);
  }, []);

  useEffect(() => {
    const fetchComments = async () => {
      try {
        const fetchedComments = await getCommentsForPost(postId);
        setComments(fetchedComments);
      } catch {
        console.error('Failed to fetch comments');
      } finally {
        setLoading(false);
      }
    };
    fetchComments();
  }, [postId]);

  const handleCommentAdded = (newComment: Comment) => {
    setComments((prevComments) => [newComment, ...prevComments]);
  };
  
  const handleCommentDeleted = async (commentId: string) => {
    if (window.confirm('Are you sure you want to delete this comment?')) {
      try {
        await deleteComment(commentId);
        setComments(comments.filter((comment) => comment.id !== commentId));
      } catch {
        alert('Failed to delete comment.');
      }
    }
  };

  if (loading) {
    return (
      <div className="mt-12 space-y-3">
        <div className="skeleton h-5 w-40" />
        <div className="skeleton h-20 w-full rounded-2xl" />
      </div>
    );
  }

  return (
    <section className="mt-14">
      <div className="mb-6 flex items-center gap-3">
        <h2 className="font-display text-2xl font-bold text-text">Comments</h2>
        <span className="rounded-full bg-surface-muted px-2.5 py-0.5 text-sm font-medium text-text-subtle">
          {comments.length}
        </span>
      </div>

      {isHydrated && isAuthenticated && (
        <AddCommentForm postId={postId} onCommentAdded={handleCommentAdded} />
      )}

      <div className="mt-8 space-y-4">
        {comments.length > 0 ? (
          comments.map((comment) => (
            <div
              key={comment.id}
              className="rounded-2xl border border-border-soft bg-surface p-5 shadow-soft transition-colors hover:border-primary/30"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-3">
                  <Avatar name={comment.user?.username} size="sm" />
                  <div>
                    <p className="text-sm font-semibold text-text">{comment.user?.username}</p>
                    <p className="text-xs text-text-subtle">
                      {/* Only render the locale-specific date on the client */}
                      {isClient ? new Date(comment.created_at).toLocaleString() : ''}
                    </p>
                  </div>
                </div>
                {isHydrated && user?.id === comment.user?.id && (
                  <button
                    onClick={() => handleCommentDeleted(comment.id)}
                    className="rounded-full px-2 py-1 text-xs font-medium text-text-subtle transition-colors hover:bg-red-500/10 hover:text-red-500"
                  >
                    Delete
                  </button>
                )}
              </div>
              <p className="mt-3 text-sm leading-relaxed text-text-light">{comment.content}</p>
            </div>
          ))
        ) : (
          <p className="rounded-2xl border border-dashed border-border-strong px-6 py-10 text-center text-sm text-text-subtle">
            Be the first to comment!
          </p>
        )}
      </div>
    </section>
  );
}


