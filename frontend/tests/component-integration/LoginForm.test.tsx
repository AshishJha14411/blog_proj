import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import LoginForm from '@/components/common/LoginForm';
import { loginUser, getMe } from '@/services/authService';
import { useAuthStore } from '@/stores/authStore'; // <-- Import the real store

// --- (A) MOCKING THE DEPENDENCIES ---

// 1. Mock the services (API calls)
vi.mock('@/services/authService', () => ({
  loginUser: vi.fn(),
  getMe: vi.fn(),
}));

// 2. Mock the navigation
const mockRouterPush = vi.fn();
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockRouterPush,
  }),
}));

// 3. --- FIX 1: Correctly mock the Zustand store ---
//    This mock now accepts the selector function from the component.
vi.mock('@/stores/authStore');
const mockStoreLogin = vi.fn();

// --- (B) THE TEST SUITE ---

describe('LoginForm Component', () => {

  beforeEach(() => {
    vi.clearAllMocks();
    // --- THIS IS THE FIX ---
    // Tell the (now mocked) useAuthStore hook how to behave
    // when it's called with a selector function.
    (useAuthStore as vi.Mock).mockImplementation((selector) => {
      const mockState = {
        login: mockStoreLogin,
      };
      // This runs the component's selector (e.g., state => state.login)
      // against our mockState and returns the result.
      return selector(mockState);
    });
  });

  // --- Test 1: The "Happy Path" (Successful Login) ---
// --- Test 1: The "Happy Path" (Successful Login) ---
it('should log in, fetch user, update store, and redirect on success', async () => {
  const user = userEvent.setup();
  const mockTokenData = { access_token: 'fake_access_token', refresh_token: 'fake_refresh_token' };
  const mockUserData = { id: '1', username: 'testuser', email: 'test@example.com' };
  (loginUser as vi.Mock).mockResolvedValue(mockTokenData);
  (getMe as vi.Mock).mockResolvedValue(mockUserData);

  render(<LoginForm />);

  const usernameInput = screen.getByLabelText(/username/i);
  const passwordInput = screen.getByLabelText(/password/i);
  const submitButton  = screen.getByRole('button', { name: /^sign in$/i });

  await user.type(usernameInput, 'testuser');
  await user.type(passwordInput, 'testpass123');
  await user.click(submitButton);

  // Wait for loading/disabled state (matches current UI)
  await waitFor(() => {
    expect(submitButton).toBeDisabled();
    // Optional if you add it in the component:
    // expect(submitButton).toHaveAttribute('aria-busy', 'true');
  });

  await waitFor(() => {
    expect(loginUser).toHaveBeenCalledWith('testuser', 'testpass123');
    expect(getMe).toHaveBeenCalledWith(mockTokenData.access_token);
    expect(mockStoreLogin).toHaveBeenCalledWith({
      accessToken: mockTokenData.access_token,
      refreshToken: mockTokenData.refresh_token,
      user: mockUserData,
    });
    expect(mockRouterPush).toHaveBeenCalledWith('/');
  });
});


  // --- Test 2: The "Sad Path" (This test was already correct) ---
  it('should show an error message if loginUser service fails', async () => {
    
    // ARRANGE
    const user = userEvent.setup();
    (loginUser as vi.Mock).mockRejectedValue(new Error('Invalid credentials'));
    render(<LoginForm />);
    
    const usernameInput = screen.getByLabelText(/username/i);
    const passwordInput = screen.getByLabelText(/password/i);
    // Use the specific selector
    const submitButton = screen.getByRole('button', { name: /^sign in$/i });

    // ACT
    await user.type(usernameInput, 'testuser');
    await user.type(passwordInput, 'wrongpass');
    await user.click(submitButton);

    // ASSERT
    await waitFor(() => {
      expect(screen.getByText('Invalid username or password')).toBeInTheDocument();
    });
    expect(getMe).not.toHaveBeenCalled();
    expect(mockStoreLogin).not.toHaveBeenCalled();
    expect(mockRouterPush).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: /sign in$/i })).not.toBeDisabled();
  });

});