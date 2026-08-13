import React from 'react';

import { cn } from '@/lib/cn';
import { inputBase } from './Input';

type SelectProps = React.ComponentPropsWithoutRef<'select'> & {
  className?: string;
};

/**
 * Native <select> wearing the same skin as Input/Textarea.
 *
 * The default arrow is replaced with an inline SVG background so it picks up
 * the theme's text colour instead of the OS chrome grey — the one part of a
 * native select you can restyle without rebuilding the whole listbox.
 */
const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, children, ...props }, ref) => (
    <select
      ref={ref}
      className={cn(
        inputBase,
        'cursor-pointer appearance-none bg-[length:1.1rem] bg-[right_0.6rem_center] bg-no-repeat pr-9',
        "bg-[image:url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%238d837a' stroke-width='2' stroke-linecap='round'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E\")]",
        className,
      )}
      {...props}
    >
      {children}
    </select>
  ),
);

Select.displayName = 'Select';
export default Select;
