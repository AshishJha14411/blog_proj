// tests/component-integration/NotificationsBell.test.tsx

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import NotificationsBell from '@/components/common/NotificationsBell'; // Adjust path
import { useUnreadNotifications } from '@/hooks/useUnreadNotifications';
import { getNotifications, markRead, markAllRead, NotificationItem } from '@/services/notificationService';

// --- (A) MOCK THE DEPENDENCIES ---

// 1. Mock the custom hook
vi.mock('@/hooks/useUnreadNotifications');
const mockUseUnreadNotifications = useUnreadNotifications as vi.Mock;

// 2. Mock the notification service
vi.mock('@/services/notificationService', () => ({
  getNotifications: vi.fn(),
  markRead: vi.fn(),
  markAllRead: vi.fn(),
}));
const mockGetNotifications = getNotifications as vi.Mock;
const mockMarkRead = markRead as vi.Mock;
const mockMarkAllRead = markAllRead as vi.Mock;

// 3. Mock 'window.location.href'
// We must mock this, otherwise the test will try to navigate and crash
const mockWindowLocation = vi.fn();
Object.defineProperty(window, 'location', {
  value: {
    href: '', // Default value
  },
  writable: true, // Allow us to change it
});
// We will spy on the 'href' property to see if it gets set
vi.spyOn(window.location, 'href', 'set').mockImplementation(mockWindowLocation);


// --- (B) THE TEST SUITE ---

describe('NotificationsBell Component', () => {

  const mockNotification: NotificationItem = {
    id: 'notif-123',
    action: 'story_liked',
    target_type: 'story',
    target_id: 'story-abc',
    is_read: false,
    created_at: new Date().toISOString(),
    actor: { id: 'user-xyz', username: 'TestUser' }
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  // --- Test 1: Unread Count Badge ---
  it('should render the bell with an unread count badge', () => {
    // ARRANGE: Mock the hook to return 5 unread messages
    mockUseUnreadNotifications.mockReturnValue(5);

    // ACT
    render(<NotificationsBell />);

    // ASSERT
    // Find the badge by its text
    expect(screen.getByText('5')).toBeInTheDocument();
    // Check that it's on the button
    expect(screen.getByRole('button').contains(screen.getByText('5'))).toBe(true);
  });

  it('should render without a badge if unread count is 0', () => {
    // ARRANGE: Mock the hook to return 0 unread messages
    mockUseUnreadNotifications.mockReturnValue(0);

    // ACT
    render(<NotificationsBell />);

    // ASSERT
    // The `queryBy` methods return null if not found, which is what we want
    expect(screen.queryByText('0')).not.toBeInTheDocument();
  });


  // --- Test 2: Opening the Dropdown ---
  it('should fetch and display notifications when clicked', async () => {
    const user = userEvent.setup();
    // ARRANGE
    mockUseUnreadNotifications.mockReturnValue(1);
    mockGetNotifications.mockResolvedValue({ items: [mockNotification] });

    render(<NotificationsBell />);

    // ACT
    // 1. Click the bell button
    const bellButton = screen.getByRole('button');
    await user.click(bellButton);

    // ASSERT
    // 1. It should first show a loading state
    // expect(await screen.findByText('Loading…')).toBeInTheDocument();

    // // 2. The API should be called
    // expect(mockGetNotifications).toHaveBeenCalledWith(false, 10, 0);

    // 3. The notification should appear
    const item = await screen.findByText(/story liked/i);
    expect(item).toBeInTheDocument();
    
    // 4. The item should be 'font-semibold' because it's unread
    expect(item).toHaveClass('font-semibold');
  });

  it('should show "all caught up" message when no notifications', async () => {
    const user = userEvent.setup();
    // ARRANGE
    mockUseUnreadNotifications.mockReturnValue(0);
    mockGetNotifications.mockResolvedValue({ items: [] }); // API returns empty list

    render(<NotificationsBell />);

    // ACT
    await user.click(screen.getByRole('button'));

    expect(await screen.findByText(/you.re all caught up/i)).toBeInTheDocument();
    expect(mockGetNotifications).toHaveBeenCalledTimes(1);
  });


  // --- Test 3: Clicking Items ---
  it('should mark item as read and navigate when an item is clicked', async () => {
    const user = userEvent.setup();
    // ARRANGE
    mockUseUnreadNotifications.mockReturnValue(1);
    mockGetNotifications.mockResolvedValue({ items: [mockNotification] });
    mockMarkRead.mockResolvedValue({}); // Mock the API call

    render(<NotificationsBell />);

    // ACT
    // 1. Open the bell
    await user.click(screen.getByRole('button'));
    
    // 2. Find and click the notification item
    const item = await screen.findByText(/story liked/i);
    expect(item).toHaveClass('font-semibold'); // Check it's unread
    
    await user.click(item);

    // ASSERT
    // 1. Optimistic UI: The item *immediately* loses its bold style
    expect(item).not.toHaveClass('font-semibold');
    
    // 2. API Call: Wait for 'markRead' to be called
    await waitFor(() => {
      expect(mockMarkRead).toHaveBeenCalledWith('notif-123');
    });

    // 3. Navigation: Check that our mocked window.location was called
    expect(mockWindowLocation).toHaveBeenCalledWith('/stories/story-abc');
  });
  
  it('should mark all as read when "Mark all read" is clicked', async () => {
    const user = userEvent.setup();
    // ARRANGE
    mockUseUnreadNotifications.mockReturnValue(1);
    mockGetNotifications.mockResolvedValue({ items: [mockNotification] });
    mockMarkAllRead.mockResolvedValue({});

    render(<NotificationsBell />);

    // ACT
    // 1. Open the bell
    await user.click(screen.getByRole('button'));
    
    // 2. Find the unread item
    const item = await screen.findByText(/story liked/i);
    expect(item).toHaveClass('font-semibold');
    
    // 3. Click "Mark all read"
    const markAllButton = screen.getByRole('button', { name: /mark all read/i });
    await user.click(markAllButton);

    // ASSERT
    // 1. Optimistic UI: The item should no longer be bold
    expect(item).not.toHaveClass('font-semibold');
    
    // 2. API Call: Wait for 'markAllRead' to be called
    await waitFor(() => {
      expect(mockMarkAllRead).toHaveBeenCalledTimes(1);
    });
  });
});