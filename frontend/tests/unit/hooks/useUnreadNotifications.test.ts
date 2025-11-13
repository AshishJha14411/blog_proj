import React from 'react';
import { renderHook, act, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useUnreadNotifications } from '@/hooks/useUnreadNotifications';
import { getUnreadCount } from '@/services/notificationService';

vi.mock('@/services/notificationService', () => ({
  getUnreadCount: vi.fn(),
}));
const mockGetUnreadCount = getUnreadCount as unknown as vi.Mock;

const StrictWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) =>
  React.createElement(React.StrictMode, null, children);

describe('useUnreadNotifications', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.spyOn(global, 'setInterval');
    vi.spyOn(global, 'clearInterval');
    mockGetUnreadCount.mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('fetches the initial count on mount', async () => {
    mockGetUnreadCount.mockResolvedValue(5);
    
    const { result } = renderHook(() => useUnreadNotifications(), { wrapper: StrictWrapper });

    // --- THIS IS THE FIX ---
    // We must 'act' and advance the timers to allow
    // the async useEffect/load function to resolve.
    await act(async () => {
      // This flushes all pending promises (like the load() function)
      await vi.runOnlyPendingTimersAsync(); 
    });
    // --- END FIX ---
    
    // This assertion will now pass *after* the promise has resolved
    expect(result.current).toBe(5);
    expect(mockGetUnreadCount).toHaveBeenCalledTimes(2); // StrictMode double invoke
  });

  it('polls for new counts on the given interval', async () => {
    const pollMs = 30_000;
    mockGetUnreadCount
      .mockResolvedValueOnce(2) // Call 1 (Mount)
      .mockResolvedValueOnce(2) // Call 2 (Strict Mode Re-mount)
      .mockResolvedValueOnce(9); // Call 3 (From interval)

    const { result } = renderHook(() => useUnreadNotifications(pollMs), { wrapper: StrictWrapper });

    // ACT 1: Flush the initial load
    await act(async () => {
      await vi.runOnlyPendingTimersAsync();
    });
    
    // ASSERT 1: Check initial state
    expect(result.current).toBe(2);
    expect(mockGetUnreadCount).toHaveBeenCalledTimes(2);

    // ACT 2: Advance the clock by 30s
    await act(async () => {
      await vi.advanceTimersByTimeAsync(pollMs);
    });

    // ASSERT 2: Check polled state
    expect(result.current).toBe(9);
    expect(mockGetUnreadCount).toHaveBeenCalledTimes(3);
  });

  it('clears the interval on unmount', async () => {
    const pollMs = 30_000;
    mockGetUnreadCount.mockResolvedValue(1); // All calls return 1
    
    const { result, unmount } = renderHook(() => useUnreadNotifications(pollMs), { wrapper: StrictWrapper });

    // ACT 1: Initial load
    await act(async () => {
      await vi.runOnlyPendingTimersAsync();
    });
    expect(result.current).toBe(1);
    expect(mockGetUnreadCount).toHaveBeenCalledTimes(2); // StrictMode

    // ACT 2: Unmount
    unmount();
    expect(clearInterval).toHaveBeenCalled();

    // ACT 3: Advance time *after* unmount
    await act(async () => {
      await vi.advanceTimersByTimeAsync(pollMs * 2);
    });

    // ASSERT: No new calls were made
    expect(mockGetUnreadCount).toHaveBeenCalledTimes(2);
  });
});