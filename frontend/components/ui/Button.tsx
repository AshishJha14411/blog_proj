import * as React from 'react';
import { Slot } from '@radix-ui/react-slot';

export interface ButtonProps extends React.ComponentPropsWithoutRef<'button'> {
  variant?: 'primary' | 'secondary';
  asChild?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      children,
      className,
      variant = 'primary',
      asChild = false,
      disabled,                // <-- keep disabled explicit
      type,                    // <-- capture type
      ...rest
    },
    ref
  ) => {
    const base =
      'inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 disabled:opacity-50 disabled:pointer-events-none h-10 py-4 px-8';

    const variants = {
      primary:
        'bg-[var(--accent-primary)] text-white hover:bg-[var(--accent-primary-light)]',
      secondary:
        'bg-transparent border border-[var(--border-color)] text-[var(--text-main)] hover:bg-gray-100',
    } as const;

    const classes = `${base} ${variants[variant]} ${className ?? ''}`.trim();

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
