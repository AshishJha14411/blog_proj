import React from 'react';

import { cn } from '@/lib/cn';

// Allow all native input props and ensure className is accessible
type InputProps = React.ComponentPropsWithoutRef<'input'> & {
  className?: string;
};

export const inputBase =
  'mt-1 block w-full rounded-md border border-border-soft bg-surface px-3 py-2 text-sm text-text ' +
  'placeholder:text-text-subtle/70 shadow-soft transition-all duration-200 ' +
  'hover:border-border-strong ' +
  'focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/35 ' +
  'disabled:cursor-not-allowed disabled:opacity-60';

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type = 'text', ...props }, ref) => {
    return (
      <input
        ref={ref}
        type={type}                          // <-- Explicit default so JSDOM reports it
        className={cn(inputBase, className)} // <-- Merge, don't overwrite
        {...props}
      />
    );
  }
);

Input.displayName = 'Input';
export default Input;
