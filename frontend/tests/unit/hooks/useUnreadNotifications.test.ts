import React from 'react';
import { renderHook, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useUnreadNotifications, unreadCountKey } from '@/hooks/useUnreadNotifications';
import { getUnreadCount } from '@/services/notificationService';
import { useAuthStore } from '@/stores/authStore';

vi.mock('@/services/notificationService', () => ({
  getUnreadCount: vi.fn(),
}));
const mockGetUnreadCount = getUnreadCount as unknown as vi.Mock;

// The count lives in TanStack now (so marking a notification read can invalidate
// it and update the bell immediately). These tests therefore need a provider,
// and assert the observable contract rather than setInterval internals.
let queryClient: QueryClient;

function wrapper({ children }: { children: React.ReactNode }) {
  return React.createElement(
    QueryClientProvider,
    { client: queryClient },
    React.createElement(React.StrictMode, null, children),
  );
}

function signIn() {
  useAuthStore.getState().login({
    accessToken: 'test-access-token',
    refreshToken: 'test-refresh-token',
    user: { id: 'u1', username: 'tester', email: 'tester@example.com' },
  });
}

describe('useUnreadNotifications', () => {
  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false, gcTime: 0 } },
    });
    mockGetUnreadCount.mockReset();
    signIn();
  });

  afterEach(() => {
    useAuthStore.getState().logout();
    queryClient.clear();
    vi.restoreAllMocks();
  });

  it('fetches the unread count when signed in', async () => {
    mockGetUnreadCount.mockResolvedValue(5);

    const { result } = renderHook(() => useUnreadNotifications(), { wrapper });

    await waitFor(() => expect(result.current).toBe(5));
    expect(mockGetUnreadCount).toHaveBeenCalled();
  });

  it('does not call the API at all while anonymous', async () => {
    // Regression guard: an unconditional fetch on mount put a red 401 in the
    // console for every anonymous visitor.
    useAuthStore.getState().logout();
    mockGetUnreadCount.mockResolvedValue(7);

    const { result } = renderHook(() => useUnreadNotifications(), { wrapper });

    await waitFor(() => expect(result.current).toBe(0));
    expect(mockGetUnreadCount).not.toHaveBeenCalled();
  });

  it('refetches when the notifications cache is invalidated', async () => {
    // This is what makes "mark all read" drop the badge immediately instead of
    // waiting for the next poll — which is an hour away when the socket is up.
    mockGetUnreadCount.mockResolvedValue(3);
    const { result } = renderHook(() => useUnreadNotifications(), { wrapper });
    await waitFor(() => expect(result.current).toBe(3));

    mockGetUnreadCount.mockResolvedValue(0);
    await queryClient.invalidateQueries({ queryKey: ['notifications'] });

    await waitFor(() => expect(result.current).toBe(0));
  });

  it('exposes a stable shared cache key', () => {
    // The bell and the /notifications page must invalidate the same prefix.
    expect(unreadCountKey[0]).toBe('notifications');
  });

  it('fetches the real count under the app-level staleTime, starting signed out', async () => {
    // REGRESSION (production): the hook used `initialData: 0`. That seeds the
    // cache with a value stamped `dataUpdatedAt = now`, and the real app's
    // QueryClient sets `staleTime: 30_000` — so the fabricated zero counted as
    // FRESH. Because `accessToken` is memory-only, the query is disabled on the
    // first render and only becomes enabled once AuthInitializer mints a token;
    // by then the zero was still fresh, so no fetch was ever issued and the bell
    // showed 0 while the API returned 2.
    //
    // The earlier tests all passed because they build a QueryClient WITHOUT
    // staleTime (defaulting to 0), which refetches where production would not.
    // This one mirrors app/providers.tsx and starts from the signed-out state.
    useAuthStore.getState().logout();
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false, gcTime: 0, staleTime: 30_000 } },
    });
    mockGetUnreadCount.mockResolvedValue(2);

    const { result, rerender } = renderHook(() => useUnreadNotifications(), { wrapper });

    // Gate closed: no token yet, so nothing is fetched and nothing is displayed.
    expect(result.current).toBe(0);
    expect(mockGetUnreadCount).not.toHaveBeenCalled();

    // AuthInitializer lands the access token — the gate opens.
    signIn();
    rerender();

    await waitFor(() => expect(result.current).toBe(2));
  });
});
