import React from 'react';

// This allows us to pass any standard input props (like 'type', 'placeholder', etc.)
type InputProps = React.ComponentPropsWithoutRef<'input'>;

const Input = React.forwardRef<HTMLInputElement, InputProps>((props, ref) => {
  return (
    <input
      {...props}
      ref={ref}
      className="mt-1 p-2 block w-full rounded-md border-gray-300 text-text shadow-sm focus:border-primary focus:ring-primary sm:text-sm"
    />
  );
});

Input.displayName = 'Input';
export default Input;
