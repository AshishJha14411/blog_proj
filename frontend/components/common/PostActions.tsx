'use client';

import { useHydratedAuth } from '@/hooks/useHydratedAuth';
import { deletePost } from '@/services/postService';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/stores/authStore';

interface PostActionsProps {
  postAuthorId: number;
  postId: number;
}

export default function PostActions({ postAuthorId, postId }: PostActionsProps) {
  const { user, isAuthenticated, isHydrated } = useHydratedAuth();
  const router = useRouter();
  console.log(user)
  const handleDelete = async () => {
    if (window.confirm('Are you sure you want to delete this post?')) {
      try {
        await deletePost(String(postId));
        router.push('/posts');
      } catch (err) {
        alert('Failed to delete post.');
      }
    }
  };

  if (!isHydrated || !isAuthenticated) {
    return null; // Don't show anything if not logged in or not hydrated
  }

  // Show buttons if the logged-in user is the author OR if they are an admin/moderator
  const canModify = user?.id === postAuthorId || ['moderator', 'superadmin'].includes(user?.role?.name || '');

  if (canModify) {
    return (
      <div className="flex gap-2">
        <Link href={`/posts/${postId}/edit`} className="rounded-md bg-gray-200 px-3 py-1 text-sm text-text">
          Edit
        </Link>
        <button onClick={handleDelete} className="rounded-md bg-red-500 px-3 py-1 text-sm text-white">
          Delete
        </button>
      </div>
    );
  }

  return null; // Return nothing if the user is not authorized
}
