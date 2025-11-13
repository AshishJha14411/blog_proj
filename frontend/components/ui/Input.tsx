import React from 'react';

// Allow all native input props and ensure className is accessible
type InputProps = React.ComponentPropsWithoutRef<'input'> & {
  className?: string;
};

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type = 'text', ...props }, ref) => {
    const base =
      'mt-1 p-2 block w-full rounded-md border-gray-300 text-text shadow-sm focus:border-primary focus:ring-primary sm:text-sm';

    // Merge base + incoming classes
    const merged = [base, className].filter(Boolean).join(' ');

    return (
      <input
        ref={ref}
        type={type}                 // <-- Explicit default so JSDOM reports it
        className={merged}          // <-- Merge, don't overwrite
        {...props}
      />
    );
  }
);

Input.displayName = 'Input';
export default Input;
