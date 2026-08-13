import * as React from 'react';

import { cn } from '@/lib/cn';

interface PageHeaderProps {
  /** Small tracked label above the title — orients the reader in one glance. */
  eyebrow?: string;
  title: React.ReactNode;
  description?: React.ReactNode;
  actions?: React.ReactNode;
  align?: 'left' | 'center';
  className?: string;
}

/**
 * One heading treatment for every page, so /bookmarks and /myposts stop each
 * inventing their own margins and type sizes.
 */
export default function PageHeader({
  eyebrow,
  title,
  description,
  actions,
  align = 'left',
  className,
}: PageHeaderProps) {
  const centered = align === 'center';

  return (
    <div
      className={cn(
        'mb-10 flex flex-col gap-4',
        centered ? 'items-center text-center' : 'sm:flex-row sm:items-end sm:justify-between',
        className,
      )}
    >
      <div className={cn('max-w-2xl', centered && 'flex flex-col items-center')}>
        {eyebrow && (
          <span className="mb-3 inline-flex items-center gap-2 rounded-full border border-border-soft bg-surface/70 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-text-subtle backdrop-blur-sm">
            <span className="h-1 w-1 rounded-full bg-primary" />
            {eyebrow}
          </span>
        )}
        <h1 className="font-display text-3xl font-bold tracking-tight text-text sm:text-4xl">
          {title}
        </h1>
        {description && (
          <p className="mt-3 text-base leading-relaxed text-text-light">{description}</p>
        )}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-3">{actions}</div>}
    </div>
  );
}

/** Section-level heading with an optional trailing link. */
export function SectionHeading({
  title,
  hint,
  action,
  className,
}: {
  title: React.ReactNode;
  hint?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn('mb-6 flex flex-wrap items-end justify-between gap-3', className)}>
      <div>
        <h2 className="font-display text-2xl font-bold text-text">{title}</h2>
        {hint && <p className="mt-1 text-sm text-text-subtle">{hint}</p>}
      </div>
      {action}
    </div>
  );
}
