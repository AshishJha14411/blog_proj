'use client';

import React, { useEffect, useRef, useState } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { useRouter } from 'next/navigation';
import { getPendingCreatorRequests, reviewCreatorRequest, CreatorRequest } from '@/services/adminService';
import Avatar from '@/components/ui/Avatar';
import Button from '@/components/ui/Button';
import EmptyState from '@/components/ui/EmptyState';
import PageHeader from '@/components/ui/PageHeader';

export default function AdminCreatorRequestQueuePage() {
  const { user, isHydrated } = useAuth();
  const router = useRouter();

  const [requests, setRequests] = useState<CreatorRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const fetchedRef = useRef(false); // avoid duplicate fetches

  useEffect(() => {
    // 1) Don’t do anything until hydration is complete
    if (!isHydrated) return;

    // 2) If we don’t know the user yet, wait (don’t redirect)
    if (!user) return;

    // 3) Now we can decide based on the actual role
    const isModerator =
      user.role?.name === 'moderator' || user.role?.name === 'superadmin';

    if (!isModerator) {
      // Use replace to avoid back button bouncing
      router.replace('/');
      return;
    }

    // 4) Fetch once when authorized
    if (fetchedRef.current) return;
    fetchedRef.current = true;

    (async () => {
      setLoading(true);
      try {
        const data = await getPendingCreatorRequests();
        setRequests(data);
      } catch {
        setError('Failed to fetch pending requests.');
      } finally {
        setLoading(false);
      }
    })();
  }, [isHydrated, user, router]);

  // Loading UI until we’re hydrated AND have a user decision
  if (!isHydrated || !user || loading) {
    return <div className="p-8 text-center">Loading request queue...</div>;
  }

  const isModerator =
    user.role?.name === 'moderator' || user.role?.name === 'superadmin';

  if (!isModerator) {
    return (
      <div className="p-8 text-center text-red-500">
        Access Denied. Redirecting...
      </div>
    );
  }

  const handleReview = async (requestId: string, action: 'approve' | 'reject') => {
    try {
      await reviewCreatorRequest(requestId, action);
      setRequests(prev => prev.filter(req => req.id !== requestId));
    } catch {
      setError(`Failed to ${action} request. Please try again.`);
    }
  };

  return (
    <main className="mx-auto max-w-4xl px-6 py-14">
      <PageHeader
        eyebrow="Admin"
        title="Creator Request Queue"
        description="Readers asking for permission to publish."
      />

      {error && (
        <p className="mb-6 rounded-2xl border border-red-500/25 bg-red-500/10 px-4 py-3 text-sm text-red-600 dark:text-red-300">
          {error}
        </p>
      )}

      {requests.length === 0 ? (
        <EmptyState
          title="No pending requests"
          description="New creator applications land here as they come in."
        />
      ) : (
        <div className="space-y-4">
          {requests.map(req => (
            <div
              key={req.id}
              className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-border-soft bg-surface p-5 shadow-soft"
            >
              <div className="flex min-w-0 items-center gap-3">
                <Avatar name={req.user.username} size="md" />
                <div className="min-w-0">
                  <p className="font-semibold text-text">{req.user.username}</p>
                  <p className="mt-0.5 text-sm text-text-light">
                    {req.reason || 'No reason provided.'}
                  </p>
                </div>
              </div>
              <div className="flex gap-2">
                <Button size="sm" onClick={() => handleReview(req.id, 'approve')}>Approve</Button>
                <Button size="sm" variant="secondary" onClick={() => handleReview(req.id, 'reject')}>
                  Reject
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </main>
  );
}
