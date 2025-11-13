import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';

import SignupForm from '@/components/common/SignupForm';
import { signupUser } from '@/services/authService';

// --- Mocks ---
vi.mock('@/services/authService', () => ({
  signupUser: vi.fn(),
}));

const mockPush = vi.fn();
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
  }),
}));

describe('SignupForm', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('submits signup data and redirects to "/" on success', async () => {
    // Arrange
    const user = userEvent.setup();
    (signupUser as vi.Mock).mockResolvedValueOnce({ ok: true });

    render(<SignupForm />);

    // Fill the form via accessible labels
    await user.type(screen.getByLabelText(/email address/i), 'test@example.com');
    await user.type(screen.getByLabelText(/username/i), 'testuser');
    await user.type(screen.getByLabelText(/password/i), 'testpass123');

    // Act
    await user.click(screen.getByRole('button', { name: /sign up/i }));

    // Assert
    await waitFor(() => {
      expect(signupUser).toHaveBeenCalledWith({
        email: 'test@example.com',
        username: 'testuser',
        password: 'testpass123',
      });
      expect(mockPush).toHaveBeenCalledWith('/');
    });

    // Should not show an error
    expect(
      screen.queryByText(/failed to create account\. please try again\./i)
    ).not.toBeInTheDocument();
  });

  it('shows an error message when signup fails and does not redirect', async () => {
    // Arrange
    const user = userEvent.setup();
    (signupUser as vi.Mock).mockRejectedValueOnce(new Error('network'));

    render(<SignupForm />);

    await user.type(screen.getByLabelText(/email address/i), 'bad@example.com');
    await user.type(screen.getByLabelText(/username/i), 'baduser');
    await user.type(screen.getByLabelText(/password/i), 'badpass');

    // Act
    await user.click(screen.getByRole('button', { name: /sign up/i }));

    // Assert
    // Wait for error to render
    expect(
      await screen.findByText(/failed to create account\. please try again\./i)
    ).toBeInTheDocument();

    expect(mockPush).not.toHaveBeenCalled();
  });

  it('uses proper input types and required attributes', () => {
    render(<SignupForm />);

    const email = screen.getByLabelText(/email address/i);
    const username = screen.getByLabelText(/username/i);
    const password = screen.getByLabelText(/password/i);

    expect(email).toHaveAttribute('type', 'email');
    expect(username).toHaveAttribute('type', 'text');
    expect(password).toHaveAttribute('type', 'password');

    expect(email).toBeRequired();
    expect(username).toBeRequired();
    expect(password).toBeRequired();
  });
});
