import { describe, it, expect, beforeEach } from 'vitest';
// Import the real store and User type
import { useAuthStore, User } from '@/stores/authStore';

// Define a mock user and login data
const mockUser: User = {
  id: 'user-123',
  username: 'test-user',
  email: 'test@example.com',
  role: { id: 'r1', name: 'user' }
};

const mockLoginData = {
  accessToken: 'fake-token-123',
  refreshToken: 'fake-refresh-456',
  user: mockUser
};

describe('authStore (Unit Test)', () => {

  // This is crucial: we must reset the store's state
  // before each test to ensure tests are isolated.
  beforeEach(() => {
    // We use the store's own actions to reset it to a clean state
    useAuthStore.getState().logout();
    useAuthStore.getState().clearLogoutFlag();
  });

  it('should have the correct initial (logged-out) state', () => {
    const state = useAuthStore.getState();

    expect(state.accessToken).toBeNull();
    expect(state.user).toBeNull();
    expect(state.isAuthenticated).toBe(false);
    expect(state.recentlyLoggedOut).toBe(false);
  });

  it('should handle the login() action correctly', () => {
    // ACT: Call the login action
    useAuthStore.getState().login(mockLoginData);

    // ASSERT: Check the new state
    const state = useAuthStore.getState();
    expect(state.accessToken).toBe('fake-token-123');
    expect(state.user).toEqual(mockUser);
    expect(state.isAuthenticated).toBe(true);
    expect(state.recentlyLoggedOut).toBe(false); // Login should clear the flag
  });

  it('should handle the logout() action correctly', () => {
    // ARRANGE: Put the store in a logged-in state first
    useAuthStore.getState().login(mockLoginData);
    expect(useAuthStore.getState().isAuthenticated).toBe(true); // Sanity check

    // ACT: Call the logout action
    useAuthStore.getState().logout();

    // ASSERT: Check that the state is cleared
    const state = useAuthStore.getState();
    expect(state.accessToken).toBeNull();
    expect(state.user).toBeNull();
    expect(state.isAuthenticated).toBe(false);
    expect(state.recentlyLoggedOut).toBe(true); // Logout should set the flag
  });

  it('should handle the setAccessToken() action', () => {
    // ACT
    useAuthStore.getState().setAccessToken('new-access-token');
    
    // ASSERT
    const state = useAuthStore.getState();
    expect(state.accessToken).toBe('new-access-token');
    // It should *only* set the token, not change auth state
    expect(state.isAuthenticated).toBe(false);
    expect(state.user).toBeNull();
  });

  it('should handle the clearLogoutFlag() action', () => {
    // ARRANGE: Log out to set the flag
    useAuthStore.getState().logout();
    expect(useAuthStore.getState().recentlyLoggedOut).toBe(true); // Sanity check

    // ACT
    useAuthStore.getState().clearLogoutFlag();

    // ASSERT
    const state = useAuthStore.getState();
    expect(state.recentlyLoggedOut).toBe(false);
  });
});