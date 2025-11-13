// tests/unit/hooks/useModGuard.test.ts

import { renderHook } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useHydratedAuth } from '@/hooks/useHydratedAuth';
import { useModGuard } from '@/hooks/useModGuard'; // Adjust path
import { User } from '@/stores/authStore';

// --- (A) MOCK THE DEPENDENCIES ---

// 1. Mock the 'useHydratedAuth' hook that our hook depends on
vi.mock('@/hooks/useHydratedAuth');
// Mock the next/navigation module to provide a fake router
const mockRouterPush = vi.fn();
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockRouterPush,
    // Add any other router functions your hook might use (e.g., replace, prefetch)
  }),
}));
// 2. Cast the mock so we can control its return value
const mockUseHydratedAuth = useHydratedAuth as vi.Mock;

// 3. Define our mock user roles
const mockUserRole = { id: 'r1', name: 'user' };
const mockModRole = { id: 'r2', name: 'moderator' };
const mockAdminRole = { id: 'r3', name: 'superadmin' };

// --- (B) THE TEST SUITE ---

describe('useModGuard Hook', () => {

  beforeEach(() => {
    // Reset all mocks before each test
    vi.clearAllMocks();
  });

  it('should return isMod: false when user is not hydrated', () => {
    // ARRANGE: Simulate the initial, non-hydrated state
    mockUseHydratedAuth.mockReturnValue({
      user: null,
      isAuthenticated: false,
      isHydrated: false, // <-- The key
    });

    // ACT: Render the hook
    const { result } = renderHook(() => useModGuard());

    // ASSERT
    expect(result.current.isMod).toBe(false);
    expect(result.current.ready).toBe(false); // Check the 'ready' flag
  });
  
  it('should return isMod: false when user is logged out', () => {
    // ARRANGE: Simulate a hydrated, logged-out user
    mockUseHydratedAuth.mockReturnValue({
      user: null,
      isAuthenticated: false,
      isHydrated: true,
    });

    // ACT
    const { result } = renderHook(() => useModGuard());

    // ASSERT
    expect(result.current.isMod).toBe(false);
    expect(result.current.ready).toBe(true);
  });

  it('should return isMod: false when user has the "user" role', () => {
    // ARRANGE: Simulate a hydrated, regular user
    mockUseHydratedAuth.mockReturnValue({
      user: { id: 'u1', role: mockUserRole },
      isAuthenticated: true,
      isHydrated: true,
    });

    // ACT
    const { result } = renderHook(() => useModGuard());

    // ASSERT
    expect(result.current.isMod).toBe(false);
  });

  it('should return isMod: true when user has the "moderator" role', () => {
    // ARRANGE: Simulate a hydrated, moderator
    mockUseHydratedAuth.mockReturnValue({
      user: { id: 'u2', role: mockModRole },
      isAuthenticated: true,
      isHydrated: true,
    });

    // ACT
    const { result } = renderHook(() => useModGuard());

    // ASSERT
    expect(result.current.isMod).toBe(true);
  });

  it('should return isMod: true when user has the "superadmin" role', () => {
    // ARRANGE: Simulate a hydrated, superadmin
    mockUseHydratedAuth.mockReturnValue({
      user: { id: 'u3', role: mockAdminRole },
      isAuthenticated: true,
      isHydrated: true,
    });

    // ACT
    const { result } = renderHook(() => useModGuard());

    // ASSERT
    expect(result.current.isMod).toBe(true);
  });
});