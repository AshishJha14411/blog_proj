'use client';

import React, { useState, useEffect } from 'react';
import { getCommentsForPost, deleteComment, Comment } from '@/services/commentService';
import { useHydratedAuth } from '@/hooks/useHydratedAuth';
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
      } catch (error) {
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
      } catch (error) {
        alert('Failed to delete comment.');
      }
    }
  };

  if (loading) return <p className="mt-8 text-center">Loading comments...</p>;
  
  return (
    <section className="mt-12">
      <h2 className="text-2xl font-bold text-text mb-6">
        Comments ({comments.length})
      </h2>
      
      {isHydrated && isAuthenticated && (
        <AddCommentForm postId={postId} onCommentAdded={handleCommentAdded} />
      )}

      <div className="space-y-6 mt-8">
        {comments.length > 0 ? (
          comments.map((comment) => (
            <div key={comment.id} className="bg-background-alt p-4 rounded-lg shadow">
              <div className="flex justify-between items-start">
                <div>
                  <p className="font-bold text-text">{comment.user?.username}</p>
                  <p className="text-sm text-text-light">
                    {/* Only render the locale-specific date on the client */}
                    {isClient ? new Date(comment.created_at).toLocaleString() : ''}
                  </p>
                </div>
                {isHydrated && user?.id === comment.user?.id && (
                  <button onClick={() => handleCommentDeleted(comment.id)} className="text-xs text-red-500 hover:underline">
                    Delete
                  </button>
                )}
              </div>
              <p className="mt-3 text-text">{comment.content}</p>
            </div>
          ))
        ) : (
          <p className="text-text-light">Be the first to comment!</p>
        )}
      </div>
    </section>
  );
}


