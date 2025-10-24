'use client';

import React, { useEffect, useRef, useState } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { useRouter } from 'next/navigation';
import { getPendingCreatorRequests, reviewCreatorRequest, CreatorRequest } from '@/services/adminService';
import Button from '@/components/ui/Button';

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
    <div className="max-w-4xl mx-auto p-8">
      <h1 className="text-3xl font-bold mb-6 text-[var(--text-main)]">
        Creator Request Queue
      </h1>
      {error && <p className="text-sm text-red-500 mb-4">{error}</p>}
      {requests.length === 0 ? (
        <p className="text-[var(--text-subtle)]">No pending requests.</p>
      ) : (
        <div className="space-y-4">
          {requests.map(req => (
            <div
              key={req.id}
              className="p-4 border border-[var(--border-color)] rounded-lg bg-white flex justify-between items-center"
            >
              <div>
                <p className="font-semibold text-[var(--text-main)]">
                  {req.user.username}
                </p>
                <p className="text-sm text-[var(--text-subtle)] mt-1">
                  {req.reason || 'No reason provided.'}
                </p>
              </div>
              <div className="flex gap-2">
                <Button onClick={() => handleReview(req.id, 'approve')}>Approve</Button>
                <Button onClick={() => handleReview(req.id, 'reject')}>Reject</Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
