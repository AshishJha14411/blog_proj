// components/ui/FormLabel.tsx
import React from 'react';

type LabelProps = React.ComponentPropsWithoutRef<'label'> & {
  className?: string;
};

export default function FormLabel({ children, className, ...props }: LabelProps) {
  const base = 'block text-sm font-medium text-text-light';
  const merged = [base, className].filter(Boolean).join(' ');
  return (
    <label {...props} className={merged}>
      {children}
    </label>
  );
}
