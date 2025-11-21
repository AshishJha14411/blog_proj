// tests/component-integration/InteractionButtons.test.tsx

import { render, screen, waitFor,act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import InteractionButtons from '@/components/common/InteractionButtons'; // Adjust path
import { useHydratedAuth } from '@/hooks/useHydratedAuth';
// --- (A) MOCK THE DEPENDENCIES ---

// 1. Mock the 'useAuth' hook
vi.mock('@/hooks/useHydratedAuth');

// --- THIS IS THE FIX ---
const mockUseHydratedAuth = useHydratedAuth as vi.Mock;

// 2. Mock the 'interactionService'
import { toggleLike, toggleBookmark } from '@/services/interactionService';
vi.mock('@/services/interactionService', () => ({
  toggleLike: vi.fn(),
  toggleBookmark: vi.fn(),
}));
const mockToggleLike = toggleLike as vi.Mock;
const mockToggleBookmark = toggleBookmark as vi.Mock;

// 3. Mock window.alert (which your component calls on error)
vi.spyOn(window, 'alert').mockImplementation(() => {});

// --- (B) THE TEST SUITE ---

describe('InteractionButtons Component', () => {

  const fakePostId = 'post-123';

  beforeEach(() => {
    
    vi.clearAllMocks();
    // Default mock: user is logged in and hydrated
    mockUseHydratedAuth.mockReturnValue({
      isAuthenticated: true,
      isHydrated: true,
    });
  });

  // --- Test 1: Logged-Out State ---
  it('should render all buttons as disabled if user is not authenticated', () => {
    // ARRANGE: Override the mock for this one test
    mockUseHydratedAuth.mockReturnValue({
      isAuthenticated: false,
      isHydrated: true,
    });

    render(<InteractionButtons postId={fakePostId} initialLiked={false} initialBookmarked={false} />);

    // ASSERT
    // We find the buttons by their new 'aria-label'
    expect(screen.getByRole('button', { name: /like post/i })).toBeDisabled();
    expect(screen.getByRole('button', { name: /bookmark post/i })).toBeDisabled();
  });

  // --- Test 2: "Like" Happy Path ---
  it('should optimistically like and call the API', async () => {
    const user = userEvent.setup();
    // ARRANGE: Mock the API to return a successful "liked" state
    mockToggleLike.mockResolvedValue({ success: true, liked: true });

    render(<InteractionButtons postId={fakePostId} initialLiked={false} initialBookmarked={false} />);

    const likeButton = screen.getByRole('button', { name: /like post/i });

    // Check initial state (icon is not filled)
    expect(likeButton.querySelector('svg')).toHaveAttribute('fill', 'none');

    // ACT
    await user.click(likeButton);

    // ASSERT 1: (Optimistic UI) The button *immediately* fills, even before the API call finishes.
    // Its label also changes.
    const unlikeButton = screen.getByRole('button', { name: /unlike post/i });
    expect(unlikeButton.querySelector('svg')).toHaveAttribute('fill', 'currentColor');
    
    // ASSERT 2: (API Call) Wait for the API to be called.
    await waitFor(() => {
      expect(mockToggleLike).toHaveBeenCalledWith(fakePostId);
    });

    // ASSERT 3: (Final State) The button remains "liked"
    expect(unlikeButton).toBeInTheDocument();
  });

// --- Test 3: "Like" Sad Path (API Failure) ---
  it('should revert the optimistic "like" if the API fails', async () => {
    const user = userEvent.setup();
    
    // ARRANGE: Mock the API to REJECT slowly
    mockToggleLike.mockImplementation(() => {
      return new Promise((_, reject) => {
        setTimeout(() => reject(new Error('API Failed')), 200);
      });
    });

    render(<InteractionButtons postId={fakePostId} initialLiked={false} initialBookmarked={false} />);

    const likeButton = screen.getByRole('button', { name: /like post/i });

    // ACT
    await user.click(likeButton);

    // ASSERT 1: (Optimistic UI) Wait for the *first* re-render.
    const unlikeButton = await screen.findByRole('button', { name: /unlike post/i });
    expect(unlikeButton.querySelector('svg')).toHaveAttribute('fill', 'currentColor');

    // --- THIS IS THE FIX ---
    // ASSERT 2: (Revert State) 
    // Instead of just finding the button, we use 'waitFor' to poll
    // until our *assertion* is true. This is the most robust way.
    await waitFor(() => {
      // Find the button *inside* the poll
      const revertedButton = screen.getByRole('button', { name: /like post/i });
      // Assert on the attribute that was failing
      expect(revertedButton.querySelector('svg')).toHaveAttribute('fill', 'none');
    });
    // --- END FIX ---

    // ASSERT 3: (Side Effect) Check that the user was alerted
    expect(window.alert).toHaveBeenCalledWith('Failed to update like status.');
  });
  // --- Test 4: "Bookmark" Happy Path ---
  it('should optimistically bookmark and call the API', async () => {
    const user = userEvent.setup();
    // ARRANGE: Mock the API to return a successful "bookmarked" state
    mockToggleBookmark.mockResolvedValue({ success: true, bookmarked: true });

    render(<InteractionButtons postId={fakePostId} initialLiked={false} initialBookmarked={false} />);

    const bookmarkButton = screen.getByRole('button', { name: /bookmark post/i });
    expect(bookmarkButton.querySelector('svg')).toHaveAttribute('fill', 'none');

    // ACT
    await user.click(bookmarkButton);

    // ASSERT
    // 1. Optimistic state
    const removeBookmarkButton = screen.getByRole('button', { name: /remove bookmark/i });
    expect(removeBookmarkButton.querySelector('svg')).toHaveAttribute('fill', 'currentColor');
    
    // 2. API call
    await waitFor(() => {
      expect(mockToggleBookmark).toHaveBeenCalledWith(fakePostId);
    });

    // 3. Final state
    expect(removeBookmarkButton).toBeInTheDocument();
  });
});