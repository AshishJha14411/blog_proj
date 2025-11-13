// tests/unit/hooks/useAuth.test.ts

import { renderHook, act, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useAuthStore, User } from '@/stores/authStore';

// Import the hook we are testing
import { useAuth } from '@/hooks/useAuth'; // Adjust path if needed

// --- (A) MOCK THE ZUSTAND STORE ---

// 1. Mock the entire store module
vi.mock('@/stores/authStore');

// 2. Cast the mock so TypeScript knows it's a mock
const mockUseAuthStore = useAuthStore as vi.Mock;

// 3. Define the different states our mock store can be in
const mockLoggedInUser: User = {
  id: 'user-123',
  username: 'testuser',
  email: 'test@example.com',
  role: { id: 'r1', name: 'user' }
};

const mockLoggedInState = {
  user: mockLoggedInUser,
  accessToken: 'fake-token-123',
  isAuthenticated: true,
};

const mockLoggedOutState = {
  user: null,
  accessToken: null,
  isAuthenticated: false,
};


// --- (B) THE TEST SUITE ---

describe('useAuth Hook', () => {

  // Reset the mock's return value before each test
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // Test 1: The Server-Side / Pre-Hydration State
//   it('should return the initial (logged-out) state before hydration', () => {
//     // ARRANGE:
//     // Tell the store to be "logged in"
//     mockUseAuthStore.mockReturnValue(mockLoggedInState);

//     // ACT:
//     // Render the hook. `result.current` will be the *first* return value.
//     const { result } = renderHook(() => useAuth());

//     // ASSERT:
//     // Even though the store is "logged in", the hook's first job
//     // is to return the safe, non-hydrated state to prevent a mismatch.
//     expect(result.current.isHydrated).toBe(false);
//     expect(result.current.isAuthenticated).toBe(false);
//     expect(result.current.user).toBeNull();
//     expect(result.current.accessToken).toBeNull();
//   });

  // Test 2: The Client-Side / Post-Hydration State (Logged In)
  it('should return the hydrated, logged-in state after useEffect runs', async () => {
    // ARRANGE:
    // Tell the store to be "logged in"
    mockUseAuthStore.mockReturnValue(mockLoggedInState);

    // ACT:
    const { result } = renderHook(() => useAuth());

    // ASSERT:
    // We `await` until the `isHydrated` flag becomes true
    await waitFor(() => {
      expect(result.current.isHydrated).toBe(true);
    });

    // Now we check that the state matches the real store state
    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.user).toEqual(mockLoggedInUser);
    expect(result.current.accessToken).toBe('fake-token-123');
  });

  // Test 3: The Client-Side / Post-Hydration State (Logged Out)
  it('should return the hydrated, logged-out state after useEffect runs', async () => {
    // ARRANGE:
    // Tell the store to be "logged out"
    mockUseAuthStore.mockReturnValue(mockLoggedOutState);

    // ACT:
    const { result } = renderHook(() => useAuth());

    // ASSERT:
    await waitFor(() => {
      expect(result.current.isHydrated).toBe(true);
    });

    // Check that the state is still the logged-out state
    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.user).toBeNull();
  });

  // Test 4: The "Store Update" Test (Senior-level)
  it('should update its state when the Zustand store changes', async () => {
    // ARRANGE (Start Logged Out):
    mockUseAuthStore.mockReturnValue(mockLoggedOutState);
    const { result, rerender } = renderHook(() => useAuth());

    // Wait for initial hydration
    await waitFor(() => {
      expect(result.current.isHydrated).toBe(true);
    });
    
    // Assert we are logged out
    expect(result.current.isAuthenticated).toBe(false);

    // ACT (Simulate a Login):
    // We use `act` because this will cause a React state update
    act(() => {
      // Change the value our mock store returns
      mockUseAuthStore.mockReturnValue(mockLoggedInState);
    });
    
    // Tell Testing Library to re-render the hook (as if Zustand updated it)
    rerender();

    // ASSERT (We are now logged in):
    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.user).toEqual(mockLoggedInUser);
  });
});