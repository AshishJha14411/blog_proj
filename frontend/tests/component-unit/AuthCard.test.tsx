import React from 'react';
import { render, screen, within } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import AuthCard from '@/components/ui/AuthCard';

describe('AuthCard', () => {
  it('renders the title inside an h2', () => {
    render(<AuthCard title="Log In"><div /></AuthCard>);
    const heading = screen.getByRole('heading', { level: 2, name: /log in/i });
    expect(heading).toBeInTheDocument();
  });

  it('renders children content', () => {
    render(
      <AuthCard title="Sign Up">
        <p>Child content</p>
      </AuthCard>
    );
    expect(screen.getByText('Child content')).toBeInTheDocument();
  });

  it('wraps content with expected container structure (smoke test for layout classes)', () => {
    render(
      <AuthCard title="Title">
        <div data-testid="inner">x</div>
      </AuthCard>
    );

    // Outer container
    const outer = screen.getByTestId('inner').closest('div')?.parentElement?.parentElement;
    expect(outer).toBeInTheDocument();
    if (!outer) return;

    // Check some key layout classes are present (don’t assert the entire class string)
    expect(outer.className).toContain('flex');
    expect(outer.className).toContain('min-h-screen');

    // Inner card container (the immediate parent of heading + children)
    const card = within(outer).getByRole('heading', { level: 2 }).parentElement;
    expect(card).toBeInTheDocument();
    if (!card) return;

    expect(card.className).toContain('rounded-lg');
    expect(card.className).toContain('shadow-md');
    expect(card.className).toContain('p-8');
    expect(card.className).toContain('max-w-md');
  });

  it('applies heading typography classes (basic check)', () => {
    render(<AuthCard title="Settings"><div /></AuthCard>);
    const h2 = screen.getByRole('heading', { level: 2, name: 'Settings' });
    expect(h2.className).toContain('text-3xl');
    expect(h2.className).toContain('font-bold');
    expect(h2.className).toContain('text-text');
  });
});
