// tests/component-integration/Navbar.test.tsx

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import Navbar from '@/components/common/Navbar'; // Adjust path if needed

// --- (A) MOCK THE DEPENDENCIES ---

// 1. Mock the 'useAuth' hook, which is the Navbar's dependency
import { useAuth } from '@/hooks/useAuth';
vi.mock('@/hooks/useAuth');
const mockUseAuth = useAuth as vi.Mock;

// 2. Mock the 'authService' (for the creator request)
import { logoutUser, requestCreatorAccess } from '@/services/authService';
vi.mock('@/services/authService', () => ({
  logoutUser: vi.fn(),
  requestCreatorAccess: vi.fn(),
}));
const mockRequestCreatorAccess = requestCreatorAccess as vi.Mock;

// 3. Mock the 'authStore' (for the logout action)
import { useAuthStore } from '@/stores/authStore';
const mockLogout = vi.fn();
vi.mock('@/stores/authStore', () => ({
  useAuthStore: () => ({
    logout: mockLogout,
  }),
}));

// 4. Mock the 'next/navigation' router
const mockRouterPush = vi.fn();
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockRouterPush,
  }),
}));

// 5. Mock the 'NotificationsBell' component to simplify the test
vi.mock('@/components/common/NotificationsBell', () => ({
  default: () => <div data-testid="notifications-bell" />,
}));


// --- (B) THE TEST SUITE ---

describe('Navbar Component', () => {

  beforeEach(() => {
    vi.clearAllMocks();
  });

  // --- Test 1: Logged-Out State ---
  it('shows Login and Sign Up buttons when user is not authenticated', () => {
    
    // ARRANGE: Mock the hook to return a logged-out state
    mockUseAuth.mockReturnValue({
      user: null,
      isAuthenticated: false,
      isHydrated: true, // Mark as hydrated so the component renders
    });

    // ACT
    render(<Navbar />);

    // ASSERT
    // Check that the correct buttons are visible
    expect(screen.getByRole('link', { name: /login/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /sign up/i })).toBeInTheDocument();

    // Check that the profile/logout buttons are NOT visible
    expect(screen.queryByRole('link', { name: /profile/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /log out/i })).not.toBeInTheDocument();
  });


  // --- Test 2: Logged-In State (as "user") ---
  it('shows Profile, Logout, and "Become a Creator" buttons for a "user"', () => {
    
    // ARRANGE: Mock the hook to return a logged-in "user"
    const mockUser = {
      id: 'u1',
      username: 'testuser',
      role: { id: 'r1', name: 'user' }
    };
    mockUseAuth.mockReturnValue({
      user: mockUser,
      isAuthenticated: true,
      isHydrated: true,
      accessToken: 'fake-token' // Provide token for the creator request
    });

    // ACT
    render(<Navbar />);

    // ASSERT
    // Check that the correct buttons are visible
    expect(screen.getByRole('link', { name: /profile/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /log out/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /become a creator/i })).toBeInTheDocument();
    expect(screen.getByTestId('notifications-bell')).toBeInTheDocument();

    // Check that the "Login" button is NOT visible
    expect(screen.queryByRole('link', { name: /login/i })).not.toBeInTheDocument();
    
    // Check that "Create Story" (a creator-only link) is NOT visible
    expect(screen.queryByRole('link', { name: /create story/i })).not.toBeInTheDocument();
  });


  // --- Test 3: Logged-In State (as "creator") ---
  it('shows "Create Story" and hides "Become a Creator" for a "creator"', () => {
    
    // ARRANGE: Mock the hook to return a logged-in "creator"
    const mockCreator = {
      id: 'c1',
      username: 'creatoruser',
      role: { id: 'r2', name: 'creator' }
    };
    mockUseAuth.mockReturnValue({
      user: mockCreator,
      isAuthenticated: true,
      isHydrated: true,
    });

    // ACT
    render(<Navbar />);

    // ASSERT
    // Check that creator-specific links ARE visible
    expect(screen.getByRole('link', { name: /create story/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /generate story/i })).toBeInTheDocument();

    // Check that the "Become a Creator" button is NOT visible
    expect(screen.queryByRole('button', { name: /become a creator/i })).not.toBeInTheDocument();
  });


  // --- Test 4: Test the "Become a Creator" button flow ---
  it('calls requestCreatorAccess and shows success message on click', async () => {
    
    // ARRANGE
    const user = userEvent.setup();
    const mockUser = {
      id: 'u1',
      username: 'testuser',
      role: { id: 'r1', name: 'user' }
    };
    mockUseAuth.mockReturnValue({
      user: mockUser,
      isAuthenticated: true,
      isHydrated: true,
      accessToken: 'fake-token'
    });

    // Mock the API call to succeed
    mockRequestCreatorAccess.mockResolvedValue({ message: "Success" });

    render(<Navbar />);

    // ACT
    // 1. Find the button and click it
    const creatorButton = screen.getByRole('button', { name: /become a creator/i });
    await user.click(creatorButton);

    // ASSERT
    // 1. Check that the button changed to a loading state
    // const loadingButton = await screen.findByRole('button', { name: /submitting.../i });
    // expect(loadingButton).toBeDisabled();

    // 2. Wait for all promises to resolve
    await waitFor(() => {
      // 3. Check that the API was called correctly
      expect(mockRequestCreatorAccess).toHaveBeenCalledTimes(1);
      expect(mockRequestCreatorAccess).toHaveBeenCalledWith('', 'fake-token');
    });

    // 4. Check that the final success message is displayed
    expect(await screen.findByText('Request Submitted!')).toBeInTheDocument();
    
    // 5. The button should be gone now
    expect(screen.queryByRole('button', { name: /become a creator/i })).not.toBeInTheDocument();
  });
});