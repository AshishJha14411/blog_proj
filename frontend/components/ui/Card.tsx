'use client';

import * as React from 'react';

import { cn } from '@/lib/cn';

export interface CardProps extends React.ComponentPropsWithoutRef<'div'> {
  /** Track the cursor and paint a soft rose glow under it. */
  spotlight?: boolean;
  /** Lift + brighten the hairline border on hover. For clickable cards. */
  interactive?: boolean;
  as?: 'div' | 'article' | 'section' | 'li';
}

/**
 * The surface every panel in the app is built from.
 *
 * The spotlight is the one Aceternity flourish that genuinely needs JS. It
 * writes the pointer position straight onto the element's style as
 * --spot-x/--spot-y instead of going through React state: a card grid re-
 * rendering on every mousemove is exactly the kind of thing that makes a
 * "premium" UI feel cheap. With JS off (or on touch, where pointermove never
 * fires) the CSS default puts the glow at the top centre and nothing looks
 * broken.
 */
export default function Card({
  className,
  spotlight = false,
  interactive = false,
  as = 'div',
  children,
  onPointerMove,
  ...rest
}: CardProps) {
  // The element type is a runtime choice, so React needs it widened here; the
  // props themselves stay typed as a div's, which every option accepts.
  const Tag = as as React.ElementType;

  const handlePointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    if (spotlight) {
      const el = e.currentTarget;
      const rect = el.getBoundingClientRect();
      el.style.setProperty('--spot-x', `${e.clientX - rect.left}px`);
      el.style.setProperty('--spot-y', `${e.clientY - rect.top}px`);
    }
    onPointerMove?.(e);
  };

  return (
    <Tag
      {...rest}
      onPointerMove={handlePointerMove}
      className={cn(
        'relative rounded-2xl border border-border-soft bg-surface shadow-soft',
        'transition-all duration-300',
        spotlight && 'spotlight',
        interactive &&
          'edge-glow hover:-translate-y-1 hover:border-primary/40 hover:shadow-lift',
        className,
      )}
    >
      {children}
    </Tag>
  );
}
