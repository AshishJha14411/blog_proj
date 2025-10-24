'use client';

import { useHydratedAuth } from '@/hooks/useHydratedAuth';
import { deletePost } from '@/services/postService';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/stores/authStore';

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
    if (window.confirm('Are you sure you want to delete this post?')) {
      try {
        await deletePost(String(postId));
        router.push('/stories');
      } catch (err) {
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
         {isAI ? (
        <Link href={`/stories/${postId}/edit`} className="rounded border px-3 py-1">Edit</Link>
      ) : (
        <Link href={`/userStory/${postId}/edit`} className="rounded border px-3 py-1">Edit</Link>
      )}
        <button onClick={handleDelete} className="rounded-md bg-red-500 px-3 py-1 text-sm text-white">
          Delete
        </button>
      </div>
    );
  }

  return null; // Return nothing if the user is not authorized
}
