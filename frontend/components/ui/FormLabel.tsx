// components/ui/FormLabel.tsx
import React from 'react';

import { cn } from '@/lib/cn';

type LabelProps = React.ComponentPropsWithoutRef<'label'> & {
  className?: string;
};

export default function FormLabel({ children, className, ...props }: LabelProps) {
  return (
    <label
      {...props}
      className={cn(
        'block text-xs font-semibold uppercase tracking-[0.08em] text-text-subtle',
        className,
      )}
    >
      {children}
    </label>
  );
}
