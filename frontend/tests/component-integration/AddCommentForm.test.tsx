// tests/component-integration/AddCommentForm.test.tsx

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import AddCommentForm from '@/components/common/AddCommentForm'; // Adjust path if needed

// --- (A) MOCKING THE DEPENDENCIES ---

// 1. Mock the commentService
// We are mocking the dynamic `import('@/services/commentService')`
// that your component uses.
vi.mock('@/services/commentService', () => ({
  createComment: vi.fn(), // We create a "spy" function
}));

// 2. We need to import the mocked function so we can control it
import { createComment } from '@/services/commentService';
const mockCreateComment = createComment as vi.Mock;


// --- (B) THE TEST SUITE ---

describe('AddCommentForm Component', () => {

  // Create a "spy" for the 'onCommentAdded' prop
  const mockOnCommentAdded = vi.fn();
  const fakePostId = 'post-123';

  // Reset all mocks before each test
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // --- Test 1: The "Happy Path" (Successful Submit) ---
  it('should submit the form, call the service, and clear on success', async () => {
    
    // ARRANGE
    const user = userEvent.setup();
    const mockNewComment = { id: 'comment-456', content: 'Test comment' };

    // Tell our fake 'createComment' to return a successful promise
    mockCreateComment.mockResolvedValue(mockNewComment);

    render(
      <AddCommentForm 
        postId={fakePostId} 
        onCommentAdded={mockOnCommentAdded} 
      />
    );

    // Find the form elements
    const textarea = screen.getByPlaceholderText(/share your thoughts/i);
    const submitButton = screen.getByRole('button', { name: /post comment/i });

    // ACT
    // 1. Simulate a user typing
    await user.type(textarea, 'This is a test comment');
    
    // 2. Simulate clicking submit
    await user.click(submitButton);

    await waitFor(() => {
      // 3. Check that our API service was called correctly
      expect(mockCreateComment).toHaveBeenCalledTimes(1);
      expect(mockCreateComment).toHaveBeenCalledWith(fakePostId, 'This is a test comment');

      // 4. Check that the 'onCommentAdded' prop was called with the new comment
      expect(mockOnCommentAdded).toHaveBeenCalledTimes(1);
      expect(mockOnCommentAdded).toHaveBeenCalledWith(mockNewComment);
    });

    // 5. Check that the form cleared itself on success
    expect(screen.getByPlaceholderText(/share your thoughts/i)).toHaveValue('');
    expect(screen.queryByText(/failed to post/i)).not.toBeInTheDocument();
  });


  // --- Test 2: The "Sad Path" (API Failure) ---
  it('should show an error message if the service fails', async () => {
    
    // ARRANGE
    const user = userEvent.setup();
    
    // Tell our fake 'createComment' to REJECT with an error
    mockCreateComment.mockRejectedValue(new Error('API Failure'));

    render(
      <AddCommentForm 
        postId={fakePostId} 
        onCommentAdded={mockOnCommentAdded} 
      />
    );

    const textarea = screen.getByPlaceholderText(/share your thoughts/i);
    const submitButton = screen.getByRole('button', { name: /post comment/i });

    // ACT
    await user.type(textarea, 'This comment will fail');
    await user.click(submitButton);

    // ASSERT
    // 1. Wait for the error message to appear
    await waitFor(() => {
      expect(screen.getByText(/failed to post comment/i)).toBeInTheDocument();
    });

    // 2. Check that the "success" path was NOT taken
    expect(mockOnCommentAdded).not.toHaveBeenCalled();

    // 3. Check that the user's text is NOT cleared, so they can retry
    expect(screen.getByPlaceholderText(/share your thoughts/i)).toHaveValue('This comment will fail');
    
    // 4. Check that the button is no longer loading
    expect(screen.getByRole('button', { name: /post comment/i })).not.toBeDisabled();
  });


  // --- Test 3: The "Validation Path" (Empty Submit) ---
  it('should not submit if the content is empty or just whitespace', async () => {
    
    // ARRANGE
    const user = userEvent.setup();
    render(
      <AddCommentForm 
        postId={fakePostId} 
        onCommentAdded={mockOnCommentAdded} 
      />
    );
    
    const textarea = screen.getByPlaceholderText(/share your thoughts/i);
    const submitButton = screen.getByRole('button', { name: /post comment/i });

    // ACT 1: Click without typing
    await user.click(submitButton);

    // ACT 2: Type only whitespace and click
    await user.type(textarea, '   ');
    await user.click(submitButton);

    // ASSERT
    // The API and callback should never be called
    expect(mockCreateComment).not.toHaveBeenCalled();
    expect(mockOnCommentAdded).not.toHaveBeenCalled();
  });
});