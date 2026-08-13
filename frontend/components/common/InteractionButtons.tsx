'use client';

import React, { useState } from 'react';
import { toggleLike, toggleBookmark } from '@/services/interactionService';
import { useHydratedAuth } from '@/hooks/useHydratedAuth';

// We'll need to pass the initial liked/bookmarked status from the parent
interface InteractionButtonsProps {
  postId: string;
  initialLiked: boolean;
  initialBookmarked: boolean;
}

export default function InteractionButtons({
  postId,
  initialLiked,
  initialBookmarked,
}: InteractionButtonsProps) {
  const [liked, setLiked] = useState(initialLiked);
  const [bookmarked, setBookmarked] = useState(initialBookmarked);
  const { isAuthenticated, isHydrated } = useHydratedAuth();

  const handleLike = async () => {
    if (!isAuthenticated) return; // Or redirect to login

    // Optimistic UI update
    setLiked((prev) => !prev);

    try {
      const response = await toggleLike(postId);
      // Sync with the actual state from the server
      setLiked(response.liked!);
    } catch {
      // If the API call fails, revert the UI change
      setLiked((prev) => !prev);
      alert('Failed to update like status.');
    }
  };

  const handleBookmark = async () => {
    if (!isAuthenticated) return;

    // Optimistic UI update
    setBookmarked((prev) => !prev);

    try {
      const response = await toggleBookmark(postId);
      // Sync with the actual state from the server
      setBookmarked(response.bookmarked!);
    } catch {
      // Revert UI on failure
      setBookmarked((prev) => !prev);
      alert('Failed to update bookmark status.');
    }
  };

  if (!isHydrated) return null;

  // One pill per action: icon + word, so the control says what it does instead
  // of relying on an unlabelled glyph.
  const pill =
    'inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-medium transition-all duration-200 disabled:cursor-not-allowed disabled:opacity-60';

  return (
    <div className="flex items-center gap-3">
      <button
        onClick={handleLike}
        disabled={!isAuthenticated}
        aria-label={liked ? 'Unlike post' : 'Like post'}
        aria-pressed={liked}
        title={!isAuthenticated ? 'Log in to like this story' : undefined}
        className={`${pill} ${
          liked
            ? 'border-red-500/30 bg-red-500/10 text-red-500'
            : 'border-border-soft bg-surface text-text-light hover:border-red-500/30 hover:text-red-500'
        }`}
      >
        {/* SVG for Heart Icon */}
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className={`h-[18px] w-[18px] transition-transform duration-200 ${liked ? 'scale-110' : ''}`}
          fill={liked ? 'currentColor' : 'none'}
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 016.364 0L12 7.636l1.318-1.318a4.5 4.5 0 016.364 6.364L12 20.364l-7.682-7.682a4.5 4.5 0 010-6.364z" />
        </svg>
        {liked ? 'Liked' : 'Like'}
      </button>
      <button
        onClick={handleBookmark}
        disabled={!isAuthenticated}
        aria-label={bookmarked ? 'Remove bookmark' : 'Bookmark post'}
        aria-pressed={bookmarked}
        title={!isAuthenticated ? 'Log in to bookmark this story' : undefined}
        className={`${pill} ${
          bookmarked
            ? 'border-primary/40 bg-primary/12 text-primary-strong'
            : 'border-border-soft bg-surface text-text-light hover:border-primary/40 hover:text-primary-strong'
        }`}
      >
        {/* SVG for Bookmark Icon */}
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="h-[18px] w-[18px]"
          fill={bookmarked ? 'currentColor' : 'none'}
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
        </svg>
        {bookmarked ? 'Saved' : 'Save'}
      </button>
    </div>
  );
}