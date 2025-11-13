// tests/component-integration/PublishControls.test.tsx

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import PublishControls from '@/components/story/PublishControls'; // Adjust path if needed

// --- (A) MOCK THE DEPENDENCIES ---

// 1. Mock the 'storyService'
import { publishStory, unpublishStory } from '@/services/storyService';
vi.mock('@/services/storyService', () => ({
  publishStory: vi.fn(),
  unpublishStory: vi.fn(),
}));
const mockPublishStory = publishStory as vi.Mock;
const mockUnpublishStory = unpublishStory as vi.Mock;

// --- (B) THE TEST SUITE ---

describe('PublishControls Component', () => {

  const fakePostId = 'post-123';
  const user = userEvent.setup();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  // --- Test 1: Initial Render States ---
  it('should render as "Unpublish" if initially published', () => {
    // ARRANGE
    render(<PublishControls postId={fakePostId} isPublished={true} />);

    // ASSERT
    expect(screen.getByRole('button', { name: /unpublish/i })).toBeInTheDocument();
  });

  it('should render as "Publish" if initially unpublished', () => {
    // ARRANGE
    render(<PublishControls postId={fakePostId} isPublished={false} />);

    // ASSERT
    expect(screen.getByRole('button', { name: /publish/i })).toBeInTheDocument();
  });

  // --- Test 2: Happy Path (Publishing) ---
  it('should call publishStory and update text when "Publish" is clicked', async () => {
    
    // ARRANGE
    mockPublishStory.mockResolvedValue({}); // API call succeeds
    render(<PublishControls postId={fakePostId} isPublished={false} />);
    
    const publishButton = screen.getByRole('button', { name: /publish/i });

    // ACT
    await user.click(publishButton);

    // ASSERT
    // 1. Wait for the API call to be made
    await waitFor(() => {
      expect(mockPublishStory).toHaveBeenCalledWith(fakePostId);
    });

    // 2. The button text should optimistically update
    expect(screen.getByRole('button', { name: /unpublish/i })).toBeInTheDocument();
    
    // 3. No error should be visible
    expect(screen.queryByText(/action failed/i)).not.toBeInTheDocument();
  });

  // --- Test 3: Happy Path (Unpublishing) ---
  it('should call unpublishStory and update text when "Unpublish" is clicked', async () => {
    
    // ARRANGE
    mockUnpublishStory.mockResolvedValue({}); // API call succeeds
    render(<PublishControls postId={fakePostId} isPublished={true} />);
    
    const unpublishButton = screen.getByRole('button', { name: /unpublish/i });

    // ACT
    await user.click(unpublishButton);

    // ASSERT
    // 1. Wait for the API call
    await waitFor(() => {
      expect(mockUnpublishStory).toHaveBeenCalledWith(fakePostId);
    });

    // 2. The button text should update
    expect(screen.getByRole('button', { name: /publish/i })).toBeInTheDocument();
    
    // 3. No error
    expect(screen.queryByText(/action failed/i)).not.toBeInTheDocument();
  });

  // --- Test 4: Sad Path (API Failure) ---
  it('should show an error and not change state if the API fails', async () => {
    
    // ARRANGE
    mockPublishStory.mockRejectedValue(new Error('API Failure'));
    render(<PublishControls postId={fakePostId} isPublished={false} />);
    
    const publishButton = screen.getByRole('button', { name: /publish/i });

    // ACT
    await user.click(publishButton);

    // ASSERT
    // 1. Wait for the error message to appear
    // ASSERT
    // 1. Wait for the error message to appear
    await waitFor(() => {
      // --- THIS IS THE FIX ---
      // Look for the *actual* error message from the mock
      expect(screen.getByText(/API Failure/i)).toBeInTheDocument();
      // --- END FIX ---
    });

    // 2. The button text should NOT have changed (it's still "Publish")
    expect(screen.getByRole('button', { name: /publish/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /unpublish/i })).not.toBeInTheDocument();
  });

});