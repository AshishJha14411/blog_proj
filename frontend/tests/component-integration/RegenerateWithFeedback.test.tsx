// tests/component-integration/AddCommentForm.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import AddCommentForm from '@/components/common/AddCommentForm';

vi.mock('@/services/commentService', () => ({
  createComment: vi.fn(),
}));

import { createComment } from '@/services/commentService';
const mockCreateComment = createComment as vi.Mock;

// Helper: a robust textarea query (allows optional trailing dots/ellipsis)
const getTextarea = () =>
  screen.getByPlaceholderText(/share your thoughts\.{0,3}$/i);

describe('AddCommentForm Component', () => {
  const mockOnCommentAdded = vi.fn();
  const fakePostId = 'post-123';

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('submits content, calls service, clears field, calls callback, and (optionally) re-enables button', async () => {
    const user = userEvent.setup();
    const mockNewComment = { id: 'comment-456', content: 'Test comment' };
    mockCreateComment.mockResolvedValue(mockNewComment);

    render(<AddCommentForm postId={fakePostId} onCommentAdded={mockOnCommentAdded} />);

    const textarea = getTextarea();

    // Prefer a stable way to select the submit button:
    // 1) By role+name (works now), and:
    // 2) Fallback by role and type if label changes during loading.
    let submitButton = screen.getByRole('button', { name: /post comment/i });

    await user.type(textarea, 'This is a test comment');
    await user.click(submitButton);

    // Optional: assert "loading" disables the button
    // If your component sets disabled while posting, this will pass.
    // If not, remove these two assertions.
    // expect(
    //   screen.getByRole('button', { name: /post(ing)? comment/i })
    // ).toBeDisabled?.() ?? expect(submitButton).toBeDefined();

    await waitFor(() => {
      expect(mockCreateComment).toHaveBeenCalledTimes(1);
      expect(mockCreateComment).toHaveBeenCalledWith(fakePostId, 'This is a test comment');
      expect(mockOnCommentAdded).toHaveBeenCalledTimes(1);
      expect(mockOnCommentAdded).toHaveBeenCalledWith(mockNewComment);
    });

    // Field clears
    expect(getTextarea()).toHaveValue('');

    // No error rendered
    expect(screen.queryByText(/failed to post/i)).not.toBeInTheDocument();

    // Button no longer loading / re-enabled (tolerant to label changes)
    submitButton =
      screen.queryByRole('button', { name: /post comment/i }) ??
      screen.getByRole('button', { name: /post(ing)? comment/i });
    expect(submitButton).not.toBeDisabled();
  });

  it('shows an error message and preserves input if the service fails', async () => {
    const user = userEvent.setup();
    mockCreateComment.mockRejectedValue(new Error('API Failure'));

    render(<AddCommentForm postId={fakePostId} onCommentAdded={mockOnCommentAdded} />);

    const textarea = getTextarea();
    const submitButton =
      screen.getByRole('button', { name: /post comment/i });

    await user.type(textarea, 'This comment will fail');
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/failed to post comment/i)).toBeInTheDocument();
    });

    expect(mockOnCommentAdded).not.toHaveBeenCalled();
    expect(getTextarea()).toHaveValue('This comment will fail');
    expect(
      screen.getByRole('button', { name: /post comment/i })
    ).not.toBeDisabled();
  });

  it('does not submit if content is empty or only whitespace (trimmed)', async () => {
    const user = userEvent.setup();
    render(<AddCommentForm postId={fakePostId} onCommentAdded={mockOnCommentAdded} />);

    const textarea = getTextarea();
    const submitButton = screen.getByRole('button', { name: /post comment/i });

    // Click with empty
    await user.click(submitButton);

    // Only spaces
    await user.type(textarea, '   ');
    await user.click(submitButton);

    expect(mockCreateComment).not.toHaveBeenCalled();
    expect(mockOnCommentAdded).not.toHaveBeenCalled();
  });
});
