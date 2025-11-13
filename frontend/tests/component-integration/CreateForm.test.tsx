import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';

import CreatePostForm from '@/components/common/CreatePostForm';
import { createPost } from '@/services/postService';

// --- Mocks ---
vi.mock('@/services/postService', () => ({
  createPost: vi.fn(),
}));

const mockPush = vi.fn();
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
}));

/**
 * Mock TagInput so we can deterministically push tags.
 * It renders an input + "Add tag" button that calls setTags([...]).
 */
vi.mock('@/components/common/TagInput', () => {
  return {
    default: ({ tags, setTags }: { tags: string[]; setTags: (t: string[]) => void }) => (
      <div>
        <input aria-label="Tag name" />
        <button
          type="button"
          onClick={() => {
            // for test simplicity we push two tags
            setTags(['tech', 'react']);
          }}
        >
          Add tag
        </button>
        <div aria-label="current-tags">{JSON.stringify(tags)}</div>
      </div>
    ),
  };
});

describe('CreatePostForm', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('submits title/content + tags, calls createPost and redirects to new post', async () => {
    const user = userEvent.setup();
    (createPost as vi.Mock).mockResolvedValueOnce({ id: 'post-123' });

    render(<CreatePostForm />);

    // Fill title/content
    await user.type(screen.getByLabelText(/title/i), 'My First Post');
    await user.type(screen.getByLabelText(/content/i), 'Hello world content');

    // Add tags via mocked TagInput
    await user.click(screen.getByRole('button', { name: /add tag/i }));
    expect(screen.getByLabelText('current-tags').textContent).toContain('tech');

    // Submit
    await user.click(screen.getByRole('button', { name: /publish post/i }));

    await waitFor(() => {
      expect(createPost).toHaveBeenCalledWith({
        title: 'My First Post',
        content: 'Hello world content',
        tag_names: ['tech', 'react'],
      });
      expect(mockPush).toHaveBeenCalledWith('/userStory/post-123');
    });

    // No error shown on success
    expect(screen.queryByText(/failed to create post/i)).not.toBeInTheDocument();
  });

  it('shows an error and does not navigate if createPost throws', async () => {
    const user = userEvent.setup();
    (createPost as vi.Mock).mockRejectedValueOnce(new Error('Network'));

    render(<CreatePostForm />);

    await user.type(screen.getByLabelText(/title/i), 'Oops');
    await user.type(screen.getByLabelText(/content/i), 'Bad things happen');

    await user.click(screen.getByRole('button', { name: /publish post/i }));

    // Error message appears, no navigation
    expect(
      await screen.findByText(/failed to create post\. please try again\./i)
    ).toBeInTheDocument();
    expect(mockPush).not.toHaveBeenCalled();
  });

  it('renders required attributes and correct input types', () => {
    render(<CreatePostForm />);
    const title = screen.getByLabelText(/title/i);
    const content = screen.getByLabelText(/content/i);

    expect(title).toHaveAttribute('type', 'text');
    expect(title).toBeRequired();

    // textarea has no type attr, but should be required and have rows
    expect(content).toHaveAttribute('rows', '10');
    expect(content).toBeRequired();
  });
});
