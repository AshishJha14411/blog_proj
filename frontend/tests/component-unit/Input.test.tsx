import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import React, { createRef } from 'react';
import Input from '@/components/ui/Input';

describe('Input Component', () => {
  it('renders correctly with default props', () => {
    render(<Input placeholder="Enter text" />);
    const input = screen.getByPlaceholderText('Enter text');
    expect(input).toBeInTheDocument();
    expect(input).toHaveAttribute('type', 'text'); // defaults to text
  });

  it('accepts custom props like type and value', () => {
    render(<Input type="password" defaultValue="secret" />);
    const input = screen.getByDisplayValue('secret');
    expect(input).toHaveAttribute('type', 'password');
  });

  it('calls onChange handler when user types', () => {
    const handleChange = vi.fn();
    render(<Input onChange={handleChange} />);
    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: 'hello' } });
    expect(handleChange).toHaveBeenCalledTimes(1);
  });

  it('respects disabled prop', () => {
    render(<Input disabled />);
    const input = screen.getByRole('textbox');
    expect(input).toBeDisabled();
  });

  it('respects readOnly prop', () => {
    render(<Input readOnly defaultValue="readonly" />);
    const input = screen.getByDisplayValue('readonly');
    expect(input).toHaveAttribute('readonly');
  });

  it('forwards ref to the input element', () => {
    const ref = createRef<HTMLInputElement>();
    render(<Input ref={ref} />);
    expect(ref.current).toBeInstanceOf(HTMLInputElement);
  });

  it('applies custom className in addition to defaults', () => {
    render(<Input className="extra-class" />);
    const input = screen.getByRole('textbox');
    expect(input.className).toContain('extra-class');
    // ensure it keeps the base styles too
    expect(input.className).toContain('rounded-md');
  });
});
