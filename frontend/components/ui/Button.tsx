import React from 'react';

// 1. Define the props for the component.
// We add an optional `variant` prop to the standard button props.
export interface ButtonProps extends React.ComponentPropsWithoutRef<'button'> {
  variant?: 'primary' | 'secondary';
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  // 2. We provide a default value for the variant directly in the component's signature.
  ({ children, className, variant = 'primary', ...props }, ref) => {
    
    // Base classes that apply to all variants
    const baseClasses = 
      'inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 disabled:opacity-50 disabled:pointer-events-none h-10 py-4 px-8';

    // 3. A simple object to store the styles for each variant.
    // This is a clean way to manage different styles without extra libraries.
    const variantClasses = {
      primary: 'bg-[var(--accent-primary)] text-white hover:bg-[var(--accent-primary-light)]',
      secondary: 'bg-transparent border border-[var(--border-color)] text-[var(--text-main)] hover:bg-gray-100',
    };

    // Combine the base classes, the classes for the selected variant, and any custom classes passed in.
    const combinedClasses = `${baseClasses} ${variantClasses[variant]} ${className || ''}`;

    return (
      <button
        {...props}
        ref={ref}
        className={combinedClasses.trim()}
      >
        {children}
      </button>
    );
  }
);

Button.displayName = 'Button';
export default Button;

