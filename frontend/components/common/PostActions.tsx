'use client';

import { useHydratedAuth } from '@/hooks/useHydratedAuth';
import { deletePost } from '@/services/postService';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

interface PostActionsProps {
  postAuthorId: string;
  postId: string;
  isAI: boolean
}

export default function PostActions({ postAuthorId, postId, isAI }: PostActionsProps) {
  const { user, isAuthenticated, isHydrated } = useHydratedAuth();
  const router = useRouter();
  // console.log(user)
  const handleDelete = async () => {
    if (window.confirm('Are you sure you want to delete this story?')) {
      try {
        await deletePost(String(postId));
        router.push('/myposts');
      } catch {
        alert('Failed to delete post.');
      }
    }
  };
  // console.log(isAI)

  if (!isHydrated || !isAuthenticated) {
    return null; // Don't show anything if not logged in or not hydrated
  }

  const canModify = user?.id === postAuthorId || ['moderator', 'superadmin'].includes(user?.role?.name || '');
  // console.log(user)
  if (canModify) {
    return (
      <div className="flex gap-2">
        <Link
          href={isAI ? `/stories/${postId}/edit` : `/userStory/${postId}/edit`}
          className="inline-flex items-center gap-1.5 rounded-full border border-border-soft bg-surface px-4 py-1.5 text-sm font-medium text-text transition-colors hover:border-primary/40 hover:text-primary-strong"
        >
          <svg
            aria-hidden="true"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={1.8}
            strokeLinecap="round"
            strokeLinejoin="round"
            className="h-3.5 w-3.5"
          >
            <path d="M12 20h9M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z" />
          </svg>
          Edit
        </Link>
        <button
          onClick={handleDelete}
          className="inline-flex items-center gap-1.5 rounded-full border border-red-500/25 bg-red-500/10 px-4 py-1.5 text-sm font-medium text-red-600 transition-colors hover:bg-red-500/20 dark:text-red-300"
        >
          Delete
        </button>
      </div>
    );
  }

  return null; // Return nothing if the user is not authorized
}
