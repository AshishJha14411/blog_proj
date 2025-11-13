// tests/component-unit/Textarea.test.tsx
import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect } from 'vitest';
import Textarea from '@/components/ui/Textarea';

describe('Textarea Component', () => {
  it('renders correctly with placeholder and is in the document', () => {
    render(<Textarea placeholder="Write something" />);
    const ta = screen.getByPlaceholderText('Write something');
    expect(ta).toBeInTheDocument();
    // sanity: default role exposure as textbox
    expect(screen.getByRole('textbox')).toBe(ta);
  });

  it('accepts custom props like value and name', () => {
    render(<Textarea value="hello" onChange={() => {}} name="notes" aria-label="notes field" />);
    const ta = screen.getByLabelText('notes field') as HTMLTextAreaElement;
    expect(ta.value).toBe('hello');
    expect(ta).toHaveAttribute('name', 'notes');
  });

  it('calls onChange handler when user types', async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();
    render(<Textarea onChange={handleChange} aria-label="message" />);
    const ta = screen.getByLabelText('message');

    await user.type(ta, 'abc');
    expect(handleChange).toHaveBeenCalled();
    // ensure the DOM value updates (uncontrolled scenario)
    expect((ta as HTMLTextAreaElement).value).toBe('abc');
  });

  it('respects disabled prop', async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();
    render(<Textarea disabled onChange={handleChange} aria-label="disabled ta" />);
    const ta = screen.getByLabelText('disabled ta');
    expect(ta).toBeDisabled();

    await user.type(ta, 'x'); // should not call onChange
    expect(handleChange).not.toHaveBeenCalled();
  });

  it('respects readOnly prop', async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();
    render(<Textarea readOnly onChange={handleChange} aria-label="ro ta" defaultValue="init" />);
    const ta = screen.getByLabelText('ro ta') as HTMLTextAreaElement;
    expect(ta).toHaveAttribute('readonly');

    await user.type(ta, 'x'); // browser won’t change value in readOnly
    expect(handleChange).not.toHaveBeenCalled();
    expect(ta.value).toBe('init');
  });

  it('forwards ref to the textarea element', () => {
    const ref = React.createRef<HTMLTextAreaElement>();
    render(<Textarea ref={ref} aria-label="ref ta" />);
    expect(ref.current).toBeInstanceOf(HTMLTextAreaElement);
    expect(ref.current?.tagName).toBe('TEXTAREA');
  });

  it('applies custom className in addition to defaults (merges classes)', () => {
    render(<Textarea className="extra-class" aria-label="styled ta" />);
    const ta = screen.getByLabelText('styled ta');
    expect(ta.className).toContain('extra-class');
    // keeps base style too
    expect(ta.className).toContain('rounded-md');
  });
});
