import React from 'react';

type LabelProps = React.ComponentPropsWithoutRef<'label'>;

export default function FormLabel({ children, ...props }: LabelProps) {
  return (
    <label {...props} className="block text-sm font-medium text-text-light">
      {children}
    </label>
  );
}