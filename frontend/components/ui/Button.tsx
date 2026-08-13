import * as React from 'react';
import { Slot } from '@radix-ui/react-slot';

import { cn } from '@/lib/cn';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'subtle' | 'danger';
export type ButtonSize = 'sm' | 'md' | 'lg' | 'icon';

export interface ButtonProps extends React.ComponentPropsWithoutRef<'button'> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  asChild?: boolean;
}

const base =
  'group relative inline-flex items-center justify-center gap-2 rounded-full font-medium ' +
  'transition-all duration-200 select-none ' +
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60 focus-visible:ring-offset-2 focus-visible:ring-offset-background ' +
  'disabled:opacity-50 disabled:pointer-events-none';

const variants: Record<ButtonVariant, string> = {
  // Espresso text on rose, not white: white on #D9A6A3 sits around 2:1, which
  // failed to read at small sizes. Espresso on rose clears 7:1 and looks
  // warmer besides.
  primary:
    'bg-primary text-on-primary shadow-soft hover:bg-primary-light hover:shadow-glow hover:-translate-y-px active:translate-y-0',
  secondary:
    'border border-border-soft bg-surface text-text shadow-soft hover:border-primary/50 hover:bg-surface-muted hover:-translate-y-px active:translate-y-0',
  ghost: 'text-text-light hover:bg-surface-muted hover:text-text',
  subtle: 'bg-surface-muted text-text hover:bg-primary/15 hover:text-primary-strong',
  danger:
    'border border-red-500/25 bg-red-500/10 text-red-600 hover:bg-red-500/20 dark:text-red-300',
};

const sizes: Record<ButtonSize, string> = {
  sm: 'h-8 px-4 text-xs',
  md: 'h-10 px-6 text-sm',
  lg: 'h-12 px-8 text-base',
  icon: 'h-10 w-10 p-0 text-sm',
};

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      children,
      className,
      variant = 'primary',
      size = 'md',
      asChild = false,
      disabled,                // <-- keep disabled explicit
      type,                    // <-- capture type
      ...rest
    },
    ref
  ) => {
    const classes = cn(base, variants[variant], sizes[size], className);

    if (asChild) {
      // When asChild, we can't assume the child supports `disabled`.
      // We still pass aria-busy for accessibility/state signalling.
      return (
        <Slot
          className={classes}
          aria-busy={disabled ? 'true' : undefined} // Added for happy path login form test
          {...rest}
        >
          {children}
        </Slot>
      );
    }

    // Native <button>: forward disabled + set a safe default type.
    return (
      <button
        ref={ref}
        className={classes}
        type={type ?? 'button'}                 // Added for happy path login form test
        disabled={disabled}                     // Added for happy path login form test
        aria-busy={disabled ? 'true' : undefined} // Added for happy path login form test
        {...rest}
      >
        {children}
      </button>
    );
  }
);

Button.displayName = 'Button';
export default Button;
