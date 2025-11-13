// tests/component-integration/TagInput.test.tsx

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import TagInput from '@/components/common/TagInput'; // Adjust path if needed

describe('TagInput Component', () => {

  // Create a spy for the setTags prop
  const mockSetTags = vi.fn();
  const user = userEvent.setup();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  // Helper function to render the component with props
  const renderComponent = (initialTags: string[] = []) => {
    render(<TagInput tags={initialTags} setTags={mockSetTags} />);
    
    // Find the input by its placeholder
    return screen.getByPlaceholderText(/add tags/i);
  };

  it('renders the initial tags passed as props', () => {
    // ARRANGE
    const initialTags = ['react', 'nextjs'];
    renderComponent(initialTags);

    // ASSERT
    // Check that both tags are visible
    expect(screen.getByText('react')).toBeInTheDocument();
    expect(screen.getByText('nextjs')).toBeInTheDocument();
  });

  it('adds a new tag when user presses Enter', async () => {
    // ARRANGE
    const input = renderComponent();

    // ACT
    // 1. Type into the input
    await user.type(input, 'typescript');
    // 2. Press Enter
    await user.keyboard('{Enter}');

    // ASSERT
    // 1. Check that the 'setTags' prop was called with the new array
    expect(mockSetTags).toHaveBeenCalledTimes(1);
    expect(mockSetTags).toHaveBeenCalledWith(['typescript']);
    
    // 2. Check that the input was cleared
    expect(input).toHaveValue('');
  });

  it('adds a new tag when user presses Comma', async () => {
    // ARRANGE
    const input = renderComponent();

    // ACT
    await user.type(input, 'css,'); // userEvent types the comma

    // ASSERT
    expect(mockSetTags).toHaveBeenCalledTimes(1);
    expect(mockSetTags).toHaveBeenCalledWith(['css']);
    expect(input).toHaveValue('');
  });

  it('trims whitespace from the new tag', async () => {
    // ARRANGE
    const input = renderComponent();

    // ACT
    await user.type(input, '  spaced tag  {Enter}');

    // ASSERT
    expect(mockSetTags).toHaveBeenCalledWith(['spaced tag']);
  });

  it('does not add duplicate tags', async () => {
    // ARRANGE
    const initialTags = ['react'];
    const input = renderComponent(initialTags);

    // ACT
    await user.type(input, 'react{Enter}');

    // ASSERT
    // 'setTags' should NOT be called, because "react" already exists
    expect(mockSetTags).not.toHaveBeenCalled();
    expect(input).toHaveValue(''); // Input should still clear
  });

  it('does not add empty or whitespace-only tags', async () => {
    // ARRANGE
    const input = renderComponent();

    // ACT
    await user.type(input, '{Enter}'); // Press Enter on empty
    await user.type(input, '   {Enter}'); // Press Enter on whitespace

    // ASSERT
    expect(mockSetTags).not.toHaveBeenCalled();
  });

  it('removes a tag when the "x" button is clicked', async () => {
    // ARRANGE
    const initialTags = ['react', 'nextjs', 'tailwind'];
    renderComponent(initialTags);

    // Find the "x" button for the "nextjs" tag
    // We find the tag text, go to its parent, then find the button inside
    const tagElement = screen.getByText('nextjs');
    const removeButton = tagElement.nextElementSibling as HTMLButtonElement;
    
    expect(removeButton.tagName).toBe('BUTTON'); // Sanity check

    // ACT
    await user.click(removeButton);

    // ASSERT
    // 'setTags' should be called with the new array *without* "nextjs"
    expect(mockSetTags).toHaveBeenCalledTimes(1);
    expect(mockSetTags).toHaveBeenCalledWith(['react', 'tailwind']);
  });
});