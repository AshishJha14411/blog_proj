'use client';

import { useEffect, useState } from 'react';

import { cn } from '@/lib/cn';

type Theme = 'light' | 'dark';

/**
 * Light/dark switch.
 *
 * Deliberately provider-free: the source of truth is the `dark` class on
 * <html>, which the inline script in app/layout.tsx sets before first paint.
 * A React context would have to re-derive that anyway, and it would mean every
 * test that renders a component containing this button needs a wrapper.
 *
 * Initial state is read in an effect rather than during render — on the server
 * there is no <html class>, so reading it during render would hydrate with the
 * wrong icon.
 */
export default function ThemeToggle({ className }: { className?: string }) {
  const [theme, setTheme] = useState<Theme | null>(null);

  useEffect(() => {
    setTheme(document.documentElement.classList.contains('dark') ? 'dark' : 'light');
  }, []);

  const toggle = () => {
    const next: Theme = document.documentElement.classList.contains('dark') ? 'light' : 'dark';
    document.documentElement.classList.toggle('dark', next === 'dark');
    document.documentElement.style.colorScheme = next;
    try {
      localStorage.setItem('theme', next);
    } catch {
      // Private mode / blocked storage: the toggle still works for this page.
    }
    setTheme(next);
  };

  const isDark = theme === 'dark';

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={isDark ? 'Switch to light theme' : 'Switch to dark theme'}
      title={isDark ? 'Switch to light theme' : 'Switch to dark theme'}
      className={cn(
        'relative inline-flex h-9 w-9 items-center justify-center rounded-full',
        'border border-white/10 bg-white/5 text-on-dark/80',
        'transition-colors hover:border-primary/40 hover:bg-white/10 hover:text-primary',
        className,
      )}
    >
      {/* Both icons are rendered and cross-faded so the swap has no layout jump.
          Before the effect resolves, `theme` is null and the sun is shown — it
          matches the server output, so hydration is quiet. */}
      <svg
        aria-hidden="true"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
        className={cn(
          'absolute h-[18px] w-[18px] transition-all duration-300',
          isDark ? 'scale-50 rotate-90 opacity-0' : 'scale-100 rotate-0 opacity-100',
        )}
      >
        <circle cx="12" cy="12" r="4" />
        <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
      </svg>
      <svg
        aria-hidden="true"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
        className={cn(
          'absolute h-[18px] w-[18px] transition-all duration-300',
          isDark ? 'scale-100 rotate-0 opacity-100' : 'scale-50 -rotate-90 opacity-0',
        )}
      >
        <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z" />
      </svg>
    </button>
  );
}
