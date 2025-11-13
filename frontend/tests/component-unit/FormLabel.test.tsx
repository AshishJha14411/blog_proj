import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import FormLabel from '@/components/ui/FormLabel';

describe('FormLabel', () => {
  it('renders its children', () => {
    render(<FormLabel>Username</FormLabel>);
    expect(screen.getByText('Username')).toBeInTheDocument();
  });

  it('forwards htmlFor to associate with an input', () => {
    render(
      <div>
        <FormLabel htmlFor="u">User</FormLabel>
        <input id="u" />
      </div>
    );
    // Accessibility query should find the input by label text
    const input = screen.getByLabelText('User');
    expect(input).toBeInTheDocument();
  });

  it('merges custom className with base classes', () => {
    render(<FormLabel className="extra">Email</FormLabel>);
    const label = screen.getByText('Email');
    expect(label).toHaveClass('block', { exact: false }); // base class present
    expect(label).toHaveClass('extra', { exact: false }); // custom merged
  });

  it('forwards arbitrary props (e.g., id/aria-*)', () => {
    render(<FormLabel id="lbl" aria-live="polite">Live</FormLabel>);
    const label = screen.getByText('Live');
    expect(label).toHaveAttribute('id', 'lbl');
    expect(label).toHaveAttribute('aria-live', 'polite');
  });

  it('supports ref forwarding to the label element', () => {
    const ref = React.createRef<HTMLLabelElement>();
    render(<FormLabel ref={ref}>Ref target</FormLabel>);
    expect(ref.current).toBeInstanceOf(HTMLLabelElement);
  });
});
