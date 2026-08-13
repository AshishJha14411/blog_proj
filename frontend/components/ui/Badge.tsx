import * as React from 'react';

import { cn } from '@/lib/cn';

export type BadgeTone = 'rose' | 'neutral' | 'warning' | 'success' | 'danger' | 'info';

const tones: Record<BadgeTone, string> = {
  rose: 'border-primary/30 bg-primary/12 text-primary-strong',
  neutral: 'border-border-soft bg-surface-muted text-text-light',
  warning: 'border-amber-500/30 bg-amber-500/12 text-amber-700 dark:text-amber-300',
  success: 'border-emerald-500/30 bg-emerald-500/12 text-emerald-700 dark:text-emerald-300',
  danger: 'border-red-500/30 bg-red-500/12 text-red-600 dark:text-red-300',
  info: 'border-sky-500/30 bg-sky-500/12 text-sky-700 dark:text-sky-300',
};

export interface BadgeProps extends React.ComponentPropsWithoutRef<'span'> {
  tone?: BadgeTone;
  /** Small leading dot — reads as a status light rather than a label. */
  dot?: boolean;
}

export default function Badge({
  tone = 'neutral',
  dot = false,
  className,
  children,
  ...rest
}: BadgeProps) {
  return (
    <span
      {...rest}
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5',
        'text-xs font-medium whitespace-nowrap',
        tones[tone],
        className,
      )}
    >
      {dot && <span className="h-1.5 w-1.5 rounded-full bg-current opacity-80" />}
      {children}
    </span>
  );
}
