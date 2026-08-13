// components/ui/AuthCard.tsx
import Link from 'next/link';

import { cn } from '@/lib/cn';

interface AuthCardProps {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}

/**
 * NOTE ON STRUCTURE: the card must stay a *direct* child of the outer wrapper,
 * and `children` must stay direct children of the card. AuthCard.test.tsx walks
 * the tree by parentElement to smoke-test the layout, so an extra wrapper div
 * around either would break it — and would be an unnecessary node anyway.
 */
export default function AuthCard({ title, subtitle, children }: AuthCardProps) {
  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-background px-4 py-16">
      {/* Ambient layer: drifting rose aurora over a dot field, both masked so
          they fade well before the card's edges. Purely decorative. */}
      <div aria-hidden="true" className="aurora" />
      <div
        aria-hidden="true"
        className="bg-dots mask-radial pointer-events-none absolute inset-0 opacity-60"
      />

      <div className="edge-glow relative w-full max-w-md rounded-2xl border border-border-soft bg-surface/90 p-8 shadow-lift backdrop-blur-sm">
        <Link
          href="/"
          className="mb-6 flex items-center justify-center gap-2 text-sm font-medium text-text-subtle transition-colors hover:text-primary-strong"
        >
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-primary" />
          Quill &amp; Code
        </Link>

        <h2
          className={cn(
            'text-center font-display text-3xl font-bold text-text',
            subtitle ? 'mb-2' : 'mb-6',
          )}
        >
          {title}
        </h2>
        {subtitle && <p className="mb-6 text-center text-sm text-text-light">{subtitle}</p>}
        {children}
      </div>
    </div>
  );
}
