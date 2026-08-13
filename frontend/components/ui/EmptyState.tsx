import * as React from 'react';

import { cn } from '@/lib/cn';

/**
 * The "nothing here yet" panel. Dashed, quiet, and always says what to do next
 * — an empty grid with no explanation reads as a failed request.
 */
export default function EmptyState({
  icon,
  title,
  description,
  action,
  className,
}: {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center rounded-2xl border border-dashed border-border-strong',
        'bg-surface/50 px-6 py-14 text-center',
        className,
      )}
    >
      {icon && (
        <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full border border-border-soft bg-primary/10 text-primary-strong">
          {icon}
        </div>
      )}
      <p className="font-display text-lg font-semibold text-text">{title}</p>
      {description && (
        <p className="mt-2 max-w-sm text-sm leading-relaxed text-text-light">{description}</p>
      )}
      {action && <div className="mt-6">{action}</div>}
    </div>
  );
}
